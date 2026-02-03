#!/usr/bin/env python3
"""
Fetch missing posts from FB API that aren't in CSV data.
CSV data is prioritized (has views/reach), API ONLY fills gaps for dates NOT in CSV.

Usage:
    python fetch_missing_posts.py           # Normal mode (sends notifications)
    python fetch_missing_posts.py --silent  # Silent mode (no notifications)
"""

import json
import sqlite3
import requests
import time
import sys
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

# Import database function for duplicate prevention
try:
    from database import get_page_by_name
except ImportError:
    get_page_by_name = None

# Telegram notifications - can be disabled with --silent flag
TELEGRAM_ENABLED = "--silent" not in sys.argv
try:
    from telegram_notifier import send_new_post_alert
except ImportError:
    TELEGRAM_ENABLED = False


def normalize_post_id(post_id):
    """Extract pure post ID, stripping page ID prefix if present."""
    post_id_str = str(post_id)
    if '_' in post_id_str:
        return post_id_str.split('_')[-1]
    return post_id_str

DATABASE_PATH = "data/juanstudio_analytics.db"

# Load tokens
with open("page_tokens.json", "r") as f:
    PAGE_TOKENS = json.load(f)


def get_db_page_ids():
    """Get page_ids that exist in the database."""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT page_id FROM pages')
    page_ids = set(row[0] for row in cursor.fetchall())
    conn.close()
    return page_ids


def get_existing_post_ids():
    """Get all post IDs already in database."""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT post_id FROM posts")
    ids = set(row[0] for row in cursor.fetchall())
    conn.close()
    return ids


def fetch_posts_from_api(token, page_id, page_name, days_back=14):
    """Fetch recent posts from FB API."""
    since_date = datetime.now() - timedelta(days=days_back)
    fields = "id,message,created_time,permalink_url,reactions.summary(total_count),comments.summary(total_count),shares"

    all_posts = []
    url = f"https://graph.facebook.com/v21.0/{page_id}/posts"
    # Note: since filter can cause inconsistent results, using limit=100 to get recent posts
    params = {
        "access_token": token,
        "fields": fields,
        "limit": 100
    }

    while True:
        try:
            resp = requests.get(url, params=params)
            data = resp.json()

            if "error" in data:
                print(f"  [{page_name}] API Error: {data['error'].get('message', 'Unknown')}")
                break

            posts = data.get("data", [])
            all_posts.extend(posts)

            paging = data.get("paging", {})
            next_url = paging.get("next")

            if next_url:
                url = next_url
                params = {}
            else:
                break

            time.sleep(0.1)
        except Exception as e:
            print(f"  [{page_name}] Error: {e}")
            break

    return all_posts


def extract_post_details(post):
    """Extract reactions, comments, shares, post_type from post data."""
    reactions = post.get("reactions", {}).get("summary", {}).get("total_count", 0)
    comments = post.get("comments", {}).get("summary", {}).get("total_count", 0)
    shares = post.get("shares", {}).get("count", 0)
    # Default to Videos since most content is video - attachments field removed due to API issues
    post_type = "Videos"
    return reactions, comments, shares, post_type


def get_post_details(token, post_id):
    """DEPRECATED - Returns zeros. Use extract_post_details instead."""
    # This function no longer works due to API permission issues
    # Kept for backwards compatibility but returns zeros
    return 0, 0, 0, "Videos"


def _old_get_post_details(token, post_id):
    """Old implementation - kept for reference only."""
    try:
        url = f"https://graph.facebook.com/v21.0/{post_id}"
        params = {
            "access_token": token,
            "fields": "reactions.summary(total_count),comments.summary(total_count),shares"
        }
        resp = requests.get(url, params=params)
        data = resp.json()

        reactions = data.get("reactions", {}).get("summary", {}).get("total_count", 0)
        comments = data.get("comments", {}).get("summary", {}).get("total_count", 0)
        shares = data.get("shares", {}).get("count", 0)

        attachments = data.get("attachments", {}).get("data", [])
        if attachments:
            media_type = attachments[0].get("media_type", "").lower()
            if media_type == "video":
                post_type = "Videos"
            elif media_type == "photo":
                post_type = "Photos"
            else:
                post_type = "Text"
        else:
            post_type = "Text"

        return reactions, comments, shares, post_type
    except:
        return 0, 0, 0, "Text"


def save_post(conn, page_id, post_id, post_data, reactions, comments, shares, post_type):
    """Save a NEW post to database."""
    cursor = conn.cursor()
    now = datetime.now().isoformat()

    total_engagement = reactions + comments + shares
    pes = (reactions * 1.0) + (comments * 2.0) + (shares * 3.0)

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
    return cursor.rowcount > 0


def update_post_engagement(conn, post_id, reactions, comments, shares):
    """Update engagement data for existing API posts (no views/reach)."""
    cursor = conn.cursor()
    now = datetime.now().isoformat()

    total_engagement = reactions + comments + shares
    pes = (reactions * 1.0) + (comments * 2.0) + (shares * 3.0)

    # Only update posts that have NO views data (API posts, not CSV)
    cursor.execute("""
        UPDATE posts
        SET reactions_total = ?,
            comments_count = ?,
            shares_count = ?,
            pes = ?,
            total_engagement = ?,
            fetched_at = ?
        WHERE post_id = ?
        AND (views_count IS NULL OR views_count = 0)
    """, (reactions, comments, shares, pes, total_engagement, now, post_id))
    return cursor.rowcount > 0


def main():
    print("=" * 60)
    print("Fetching Missing Posts from FB API")
    print("=" * 60)

    # Get existing post IDs
    existing_ids = get_existing_post_ids()
    print(f"Existing posts in database: {len(existing_ids)}")

    # Get valid page IDs from database
    db_page_ids = get_db_page_ids()
    print(f"Pages in database: {len(db_page_ids)}")

    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    total_new = 0

    for label, data in PAGE_TOKENS.items():
        page_id = data.get("page_id")
        page_name = data.get("page_name", label)
        token = data.get("page_access_token")

        if not token or not page_id:
            continue

        # Use page_id directly (must match database)
        db_page_id = page_id

        print(f"\n[{page_name}] Fetching recent posts...")

        posts = fetch_posts_from_api(token, page_id, page_name, days_back=7)
        print(f"  Found {len(posts)} posts from API")

        # Filter to only new posts NOT in database (normalize IDs for comparison)
        new_posts = [p for p in posts if normalize_post_id(p["id"]) not in existing_ids]
        print(f"  New posts not in database: {len(new_posts)}")

        # Save new posts (only skip if post already exists in DB)
        page_new = 0
        for post in new_posts:
            full_post_id = post["id"]
            normalized_id = normalize_post_id(full_post_id)
            created_time = post.get("created_time", "")
            post_date = created_time[:10] if created_time else ""

            reactions, comments, shares, post_type = extract_post_details(post)

            if save_post(conn, db_page_id, normalized_id, post, reactions, comments, shares, post_type):
                page_new += 1
                print(f"  + Added ({post_date}): {normalized_id[:25]}...")

                # Send Telegram notification for new post
                if TELEGRAM_ENABLED:
                    try:
                        send_new_post_alert(
                            page_name=page_name,
                            post_type=post_type,
                            title=post.get("message", ""),
                            permalink=post.get("permalink_url", ""),
                            publish_time=created_time
                        )
                        print(f"  -> Telegram alert sent!")
                    except Exception as e:
                        print(f"  -> Telegram error: {e}")

        # Update existing API posts (refresh engagement data)
        existing_posts = [p for p in posts if normalize_post_id(p["id"]) in existing_ids]
        page_updated = 0
        for post in existing_posts:
            normalized_id = normalize_post_id(post["id"])
            reactions, comments, shares, post_type = extract_post_details(post)
            if update_post_engagement(conn, normalized_id, reactions, comments, shares):
                page_updated += 1

        if page_updated > 0:
            print(f"  ~ Updated {page_updated} existing posts")

        total_new += page_new

    conn.commit()
    conn.close()

    print("\n" + "=" * 60)
    print(f"DONE! Added {total_new} new posts from API")
    print("=" * 60)


if __name__ == "__main__":
    main()
