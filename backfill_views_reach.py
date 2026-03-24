#!/usr/bin/env python3
"""Backfill views/reach from FB API post insights.

Uses post_impressions_unique (reach) and post_video_views (views)
for posts that have 0 views/reach (typically because CSV wasn't available).
"""

import json
import sqlite3
import requests
import time
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.stdout.reconfigure(encoding='utf-8')

DATABASE_PATH = "data/juanstudio_analytics.db"

with open("page_tokens.json") as f:
    PAGE_TOKENS = json.load(f)

# Build page_id -> token lookup
TOKEN_MAP = {}
for label, data in PAGE_TOKENS.items():
    pid = data.get("page_id")
    tok = data.get("page_access_token")
    if pid and tok:
        TOKEN_MAP[pid] = tok


def get_post_insights(post_id, page_id):
    """Fetch reach and views for a single post."""
    token = TOKEN_MAP.get(page_id)
    if not token:
        return None, None

    # Need full post ID format: pageId_postId
    full_id = f"{page_id}_{post_id}" if "_" not in str(post_id) else str(post_id)

    reach = None
    views = None

    try:
        # Fetch reach
        url = f"https://graph.facebook.com/v21.0/{full_id}/insights"
        params = {"access_token": token, "metric": "post_impressions_unique"}
        resp = requests.get(url, params=params, timeout=10)
        data = resp.json()
        if "data" in data and data["data"]:
            reach = data["data"][0].get("values", [{}])[0].get("value", 0)

        # Fetch views
        params["metric"] = "post_video_views"
        resp = requests.get(url, params=params, timeout=10)
        data = resp.json()
        if "data" in data and data["data"]:
            views = data["data"][0].get("values", [{}])[0].get("value", 0)

    except Exception as e:
        pass

    return reach, views


def main():
    print("=" * 60)
    print("Backfilling Views/Reach from API Insights")
    print("=" * 60)

    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Get posts missing views/reach
    cursor.execute("""
        SELECT p.post_id, p.page_id, pg.page_name, p.publish_time
        FROM posts p
        LEFT JOIN pages pg ON p.page_id = pg.page_id
        WHERE p.publish_time >= '2026-03-01'
        AND (p.views_count IS NULL OR p.views_count = 0)
        AND (p.reactions_total > 0 OR p.comments_count > 0 OR p.shares_count > 0)
        ORDER BY p.publish_time DESC
    """)
    posts = [dict(r) for r in cursor.fetchall()]
    print(f"Posts to backfill: {len(posts)}")

    if not posts:
        print("Nothing to do!")
        return

    updated = 0
    failed = 0
    skipped = 0

    # Process in batches with threading (5 concurrent to avoid rate limits)
    def process_post(post):
        reach, views = get_post_insights(post["post_id"], post["page_id"])
        return post, reach, views

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(process_post, p): p for p in posts}

        for i, future in enumerate(as_completed(futures)):
            post, reach, views = future.result()

            if reach is None and views is None:
                skipped += 1
                continue

            reach = reach or 0
            views = views or 0

            if reach > 0 or views > 0:
                cursor.execute("""
                    UPDATE posts SET
                        views_count = MAX(COALESCE(views_count, 0), ?),
                        reach_count = MAX(COALESCE(reach_count, 0), ?)
                    WHERE post_id = ?
                """, (views, reach, post["post_id"]))
                updated += 1
            else:
                failed += 1

            # Progress every 50
            done = i + 1
            if done % 50 == 0 or done == len(posts):
                print(f"  Progress: {done}/{len(posts)} ({updated} updated, {failed} no data, {skipped} skipped)")

            # Small delay to avoid rate limits
            time.sleep(0.05)

    conn.commit()
    conn.close()

    print(f"\n{'=' * 60}")
    print(f"DONE!")
    print(f"  Updated: {updated} posts with views/reach")
    print(f"  No data: {failed}")
    print(f"  Skipped: {skipped} (no token)")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
