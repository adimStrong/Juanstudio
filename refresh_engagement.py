#!/usr/bin/env python3
"""Refresh engagement data for ALL posts from live FB Graph API.

Uses parallel workers to update reactions/comments/shares for every post.
Run weekly or when engagement numbers seem stale/wrong.

Usage:
    python refresh_engagement.py           # Refresh all posts
    python refresh_engagement.py --month   # Refresh current month only
"""

import json
import sqlite3
import requests
import sys
import time
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

DATABASE_PATH = "data/juanstudio_analytics.db"

with open("page_tokens.json", "r") as f:
    PAGE_TOKENS = json.load(f)


def get_token_for_page(page_id):
    """Find token for a given page_id."""
    for label, data in PAGE_TOKENS.items():
        if data.get("page_id") == page_id:
            return data.get("page_access_token")
    return None


def refresh_single_post(post_id, page_id, token):
    """Fetch fresh engagement for a single post from FB API."""
    try:
        url = f"https://graph.facebook.com/v21.0/{page_id}_{post_id}"
        params = {
            "access_token": token,
            "fields": "reactions.summary(total_count),comments.summary(total_count),shares"
        }
        resp = requests.get(url, params=params, timeout=15)
        data = resp.json()

        if "error" in data:
            return post_id, None, data["error"].get("message", "Unknown")

        reactions = data.get("reactions", {}).get("summary", {}).get("total_count", 0)
        comments = data.get("comments", {}).get("summary", {}).get("total_count", 0)
        shares = data.get("shares", {}).get("count", 0)
        return post_id, (reactions, comments, shares), None
    except Exception as e:
        return post_id, None, str(e)


def main():
    month_only = "--month" in sys.argv

    print("=" * 60)
    print("Refresh Engagement from Live FB API (JuanStudio)")
    print("=" * 60)

    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row

    if month_only:
        month_start = datetime.now().strftime("%Y-%m-01")
        rows = conn.execute(
            "SELECT post_id, page_id FROM posts WHERE publish_time >= ?",
            (month_start,)
        ).fetchall()
        print(f"Refreshing posts from {month_start} onwards...")
    else:
        rows = conn.execute("SELECT post_id, page_id FROM posts").fetchall()
        print(f"Refreshing ALL posts...")

    print(f"Total posts to refresh: {len(rows)}")

    # Group posts by page for token lookup
    posts_with_tokens = []
    skipped = 0
    for row in rows:
        token = get_token_for_page(row["page_id"])
        if token:
            posts_with_tokens.append((row["post_id"], row["page_id"], token))
        else:
            skipped += 1

    if skipped:
        print(f"Skipped {skipped} posts (no token for page)")

    print(f"Refreshing {len(posts_with_tokens)} posts with 10 parallel workers...")

    updated = 0
    errors = 0
    start_time = time.time()

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {
            executor.submit(refresh_single_post, pid, pgid, tok): pid
            for pid, pgid, tok in posts_with_tokens
        }

        for i, future in enumerate(as_completed(futures), 1):
            post_id, result, error = future.result()

            if result:
                reactions, comments, shares = result
                total_engagement = reactions + comments + shares
                pes = (reactions * 1.0) + (comments * 2.0) + (shares * 3.0)
                now = datetime.now().isoformat()

                conn.execute("""
                    UPDATE posts SET
                        reactions_total = ?,
                        comments_count = ?,
                        shares_count = ?,
                        total_engagement = ?,
                        pes = ?,
                        fetched_at = ?
                    WHERE post_id = ?
                """, (reactions, comments, shares, total_engagement, pes, now, post_id))
                updated += 1
            else:
                errors += 1

            if i % 100 == 0:
                conn.commit()
                elapsed = time.time() - start_time
                rate = i / elapsed if elapsed > 0 else 0
                print(f"  Progress: {i}/{len(posts_with_tokens)} ({rate:.1f}/sec) - {updated} updated, {errors} errors")

    conn.commit()
    conn.close()

    elapsed = time.time() - start_time
    print(f"\n{'=' * 60}")
    print(f"DONE in {elapsed:.1f}s")
    print(f"Updated: {updated}, Errors: {errors}, Total: {len(posts_with_tokens)}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
