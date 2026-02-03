#!/usr/bin/env python3
"""
Fix posts with missing titles and permalinks by re-fetching from Facebook API.
"""

import json
import sqlite3
import requests
import time

DATABASE_PATH = "data/juanstudio_analytics.db"

# Load tokens
with open("page_tokens.json", "r") as f:
    PAGE_TOKENS = json.load(f)

# Build page_id to token mapping
PAGE_ID_TO_TOKEN = {}
PAGE_ID_TO_NAME = {}
for label, data in PAGE_TOKENS.items():
    pid = data.get("page_id")
    if pid:
        PAGE_ID_TO_TOKEN[pid] = data.get("page_access_token")
        PAGE_ID_TO_NAME[pid] = data.get("page_name", label)


def fetch_post_details(post_id, page_id):
    """Fetch post details from Facebook API."""
    token = PAGE_ID_TO_TOKEN.get(page_id)
    if not token:
        return None, None

    # Full post ID format: page_id_post_id
    full_post_id = f"{page_id}_{post_id}"

    url = f"https://graph.facebook.com/v21.0/{full_post_id}"
    params = {
        "access_token": token,
        "fields": "message,permalink_url"
    }

    try:
        resp = requests.get(url, params=params, timeout=30)
        data = resp.json()

        if "error" in data:
            return None, None

        message = data.get("message", "")
        permalink = data.get("permalink_url", "")
        return message, permalink
    except Exception as e:
        return None, None


def main():
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    # Get posts missing title or permalink
    cursor.execute('''
        SELECT post_id, page_id, title, permalink
        FROM posts
        WHERE (title IS NULL OR title = '' OR permalink IS NULL OR permalink = '')
        AND substr(publish_time, 1, 10) >= '2026-01-20'
    ''')

    posts_to_fix = cursor.fetchall()
    print(f"Found {len(posts_to_fix)} posts to fix")

    fixed = 0
    failed = 0

    for post_id, page_id, current_title, current_permalink in posts_to_fix:
        page_name = PAGE_ID_TO_NAME.get(page_id, "Unknown")

        message, permalink = fetch_post_details(post_id, page_id)

        updates = []
        params = []

        if message and (not current_title or current_title == ""):
            updates.append("title = ?")
            params.append(message[:200])

        if permalink and (not current_permalink or current_permalink == ""):
            updates.append("permalink = ?")
            params.append(permalink)

        if updates:
            params.append(post_id)
            sql = f"UPDATE posts SET {', '.join(updates)} WHERE post_id = ?"
            cursor.execute(sql, params)
            fixed += 1
            print(f"  [OK] Fixed post {post_id[:15]}... ({page_name})")
        else:
            failed += 1

        time.sleep(0.1)  # Rate limiting

    conn.commit()
    conn.close()

    print()
    print(f"Done! Fixed: {fixed}, Failed: {failed}")


if __name__ == "__main__":
    main()
