#!/usr/bin/env python3
"""
Fetch posts for a specific date from FB API by using deep pagination.
Since we can't use since/until params, we paginate until we find posts for the target date.

Usage:
    python fetch_date_posts.py 2026-02-02
"""

import json
import sqlite3
import requests
import sys
import time
from datetime import datetime, timedelta

DATABASE_PATH = "data/juanstudio_analytics.db"

# Load tokens
with open("page_tokens.json", "r") as f:
    PAGE_TOKENS = json.load(f)


def normalize_post_id(post_id):
    """Extract pure post ID, stripping page ID prefix if present."""
    post_id_str = str(post_id)
    if '_' in post_id_str:
        return post_id_str.split('_')[-1]
    return post_id_str


def fetch_posts_for_date(token, page_id, page_name, target_date, max_pages=10):
    """Fetch posts from FB API with engagement data.

    Uses two parallel fetches:
    1. Minimal fields - returns ALL posts (to identify target date posts)
    2. Full fields - returns SUBSET with engagement data

    Matches them by post ID to get as much engagement data as possible.
    """
    base_url = f"https://graph.facebook.com/v21.0/{page_id}/posts"

    # Phase 1: Get ALL posts with minimal fields
    minimal_posts = {}  # id -> post data
    url = base_url
    params = {"access_token": token, "fields": "id,created_time", "limit": 100}
    pages_fetched = 0
    found_target = False

    while url and pages_fetched < max_pages:
        try:
            resp = requests.get(url, params=params, timeout=30)
            data = resp.json()
            if "error" in data:
                break

            posts = data.get("data", [])
            pages_fetched += 1

            for post in posts:
                created = post.get("created_time", "")[:10]
                if created == target_date:
                    minimal_posts[post["id"]] = post
                    found_target = True

            if posts:
                oldest = posts[-1].get("created_time", "")[:10]
                if found_target and oldest < target_date:
                    break

            paging = data.get("paging", {})
            url = paging.get("next")
            params = {}
            time.sleep(0.1)

        except Exception as e:
            print(f"  [{page_name}] Error in phase 1: {e}")
            break

    if not minimal_posts:
        return [], pages_fetched

    # Phase 2: Get posts with FULL fields (may return fewer posts)
    full_fields = "id,message,created_time,permalink_url,reactions.summary(total_count),comments.summary(total_count),shares"
    full_posts = {}  # id -> post data with engagement

    url = base_url
    params = {"access_token": token, "fields": full_fields, "limit": 100}
    pages_full = 0

    while url and pages_full < max_pages:
        try:
            resp = requests.get(url, params=params, timeout=30)
            data = resp.json()
            if "error" in data:
                break

            posts = data.get("data", [])
            pages_full += 1

            for post in posts:
                post_id = post["id"]
                if post_id in minimal_posts:
                    full_posts[post_id] = post

            # Check if we have all target posts or passed target date
            if len(full_posts) == len(minimal_posts):
                break

            if posts:
                oldest = posts[-1].get("created_time", "")[:10]
                if oldest < target_date:
                    break

            paging = data.get("paging", {})
            url = paging.get("next")
            params = {}
            time.sleep(0.1)

        except Exception as e:
            print(f"  [{page_name}] Error in phase 2: {e}")
            break

    # Merge: use full data if available, otherwise minimal with zero engagement
    target_posts = []
    for post_id, minimal in minimal_posts.items():
        if post_id in full_posts:
            target_posts.append(full_posts[post_id])
        else:
            # Post exists but no engagement data available from API
            target_posts.append({
                "id": post_id,
                "created_time": minimal.get("created_time", ""),
                "message": "",
                "permalink_url": "",
                "reactions": {"summary": {"total_count": 0}},
                "comments": {"summary": {"total_count": 0}},
                "shares": {"count": 0}
            })

    found_with_engagement = len(full_posts)
    total_found = len(minimal_posts)
    if found_with_engagement < total_found:
        print(f"  Note: {total_found - found_with_engagement}/{total_found} posts without engagement data")

    return target_posts, pages_fetched


def save_post(conn, page_id, post_id, post_data, reactions, comments, shares, post_type):
    """Save or update a post in database."""
    cursor = conn.cursor()
    now = datetime.now().isoformat()

    total_engagement = reactions + comments + shares
    pes = (reactions * 1.0) + (comments * 2.0) + (shares * 3.0)

    # Try to update first
    cursor.execute("""
        UPDATE posts SET
            reactions_total = ?,
            comments_count = ?,
            shares_count = ?,
            pes = ?,
            total_engagement = ?,
            fetched_at = ?
        WHERE post_id = ?
    """, (reactions, comments, shares, pes, total_engagement, now, post_id))

    if cursor.rowcount == 0:
        # Insert new post
        cursor.execute("""
            INSERT OR IGNORE INTO posts
            (post_id, page_id, title, permalink, post_type, publish_time,
             reactions_total, comments_count, shares_count,
             pes, total_engagement, fetched_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            post_id,
            page_id,
            (post_data.get("message", "") or "")[:200],
            post_data.get("permalink_url"),
            post_type,
            post_data.get("created_time"),
            reactions,
            comments,
            shares,
            pes,
            total_engagement,
            now
        ))
        return "inserted" if cursor.rowcount > 0 else "skipped"
    return "updated"


def main():
    if len(sys.argv) < 2:
        print("Usage: python fetch_date_posts.py YYYY-MM-DD")
        print("Example: python fetch_date_posts.py 2026-02-02")
        sys.exit(1)

    target_date = sys.argv[1]

    # Validate date format
    try:
        datetime.strptime(target_date, "%Y-%m-%d")
    except ValueError:
        print(f"Invalid date format: {target_date}")
        print("Use YYYY-MM-DD format")
        sys.exit(1)

    print("=" * 60)
    print(f"Fetching Posts for {target_date}")
    print("=" * 60)

    conn = sqlite3.connect(DATABASE_PATH)
    total_found = 0
    total_inserted = 0
    total_updated = 0

    for label, data in PAGE_TOKENS.items():
        page_id = data.get("page_id")
        page_name = data.get("page_name", label)
        token = data.get("page_access_token")

        if not token or not page_id:
            continue

        print(f"\n[{page_name}] Searching for {target_date} posts...")

        posts, pages_fetched = fetch_posts_for_date(token, page_id, page_name, target_date, max_pages=10)

        if posts:
            print(f"  Found {len(posts)} posts (searched {pages_fetched} pages)")
            total_found += len(posts)

            for post in posts:
                post_id = normalize_post_id(post["id"])
                reactions = post.get("reactions", {}).get("summary", {}).get("total_count", 0)
                comments = post.get("comments", {}).get("summary", {}).get("total_count", 0)
                shares = post.get("shares", {}).get("count", 0)

                result = save_post(conn, page_id, post_id, post, reactions, comments, shares, "Videos")
                if result == "inserted":
                    total_inserted += 1
                    print(f"    + Inserted: {post_id[:20]}...")
                elif result == "updated":
                    total_updated += 1
        else:
            print(f"  No posts found (searched {pages_fetched} pages)")

    conn.commit()
    conn.close()

    print("\n" + "=" * 60)
    print(f"DONE! Found {total_found} posts for {target_date}")
    print(f"  Inserted: {total_inserted}")
    print(f"  Updated: {total_updated}")
    print("=" * 60)

    # Show current DB count for target date
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT COUNT(*) FROM posts
        WHERE substr(publish_time, 1, 10) = ?
    """, (target_date,))
    db_count = cursor.fetchone()[0]
    conn.close()

    print(f"\nDatabase now has {db_count} posts for {target_date}")


if __name__ == "__main__":
    main()
