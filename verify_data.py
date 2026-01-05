#!/usr/bin/env python3
"""
Verify data integrity before pushing to production.
Returns exit code 0 if OK, 1 if issues found.
"""

import sqlite3
import json
import sys

DATABASE_PATH = "data/juanstudio_analytics.db"
JSON_PATH = "frontend/public/data/analytics-v2.json"

def verify():
    print("=" * 60)
    print("DATA VERIFICATION")
    print("=" * 60)

    errors = []
    warnings = []

    # Check database
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cur = conn.cursor()

        # Check pages count
        cur.execute("SELECT COUNT(*) FROM pages")
        page_count = cur.fetchone()[0]
        print(f"Pages in database: {page_count}")

        if page_count < 14:
            errors.append(f"Missing pages! Expected 14, found {page_count}")

        # Check posts count
        cur.execute("SELECT COUNT(*) FROM posts")
        post_count = cur.fetchone()[0]
        print(f"Posts in database: {post_count}")

        if post_count < 100:
            errors.append(f"Too few posts! Expected 100+, found {post_count}")

        # Check for duplicate post IDs (with underscore = not normalized)
        cur.execute("SELECT post_id FROM posts")
        all_ids = [row[0] for row in cur.fetchall()]
        with_underscore = [id for id in all_ids if '_' in str(id)]

        if with_underscore:
            warnings.append(f"{len(with_underscore)} posts have unnormalized IDs (contain underscore)")

        # Check followers
        cur.execute("SELECT COUNT(*) FROM pages WHERE followers_count > 0")
        pages_with_followers = cur.fetchone()[0]
        print(f"Pages with followers: {pages_with_followers}")

        if pages_with_followers < 14:
            warnings.append(f"Some pages missing follower data ({14 - pages_with_followers} pages)")

        conn.close()

    except Exception as e:
        errors.append(f"Database error: {e}")

    # Check JSON export
    try:
        with open(JSON_PATH, 'r') as f:
            data = json.load(f)

        json_posts = len(data.get('posts', []))
        json_pages = len(data.get('pages', []))

        print(f"JSON posts: {json_posts}")
        print(f"JSON pages: {json_pages}")

        if json_pages < 14:
            errors.append(f"JSON missing pages! Expected 14, found {json_pages}")

        if json_posts < 100:
            errors.append(f"JSON too few posts! Expected 100+, found {json_posts}")

    except Exception as e:
        errors.append(f"JSON error: {e}")

    # Print results
    print()

    if warnings:
        print("WARNINGS:")
        for w in warnings:
            print(f"  - {w}")
        print()

    if errors:
        print("ERRORS:")
        for e in errors:
            print(f"  - {e}")
        print()
        print("VERIFICATION FAILED - Do not push!")
        return 1
    else:
        print("VERIFICATION PASSED - Safe to push!")
        return 0


if __name__ == "__main__":
    sys.exit(verify())
