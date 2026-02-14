#!/usr/bin/env python3
"""
Fix CSV Import: Match CSV rows to existing DB posts by page_name + publish_time,
update views/reach, and clean up corrupted E+ post IDs.

This avoids the Excel scientific notation problem by NOT using post_ids from CSV.
"""

import csv
import sqlite3
from datetime import datetime, timedelta

CSV_PATH = r"exports\from content manual Export\Dec-31-2025_Feb-11-2026_1460887702334520.csv"
DB_PATH = r"data\juanstudio_analytics.db"
PHT_OFFSET = timedelta(hours=8)


def parse_time(t):
    """Parse various time formats."""
    if not t:
        return None
    t = t.strip()
    if t.endswith('+0000'):
        t = t[:-5]
    for fmt in ['%Y-%m-%dT%H:%M:%S', '%m/%d/%Y %H:%M', '%m/%d/%Y %H:%M:%S']:
        try:
            return datetime.strptime(t, fmt)
        except ValueError:
            pass
    return None


def main():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")

    # =========================================================================
    # STEP 1: Build DB index (page_name + time -> post_id)
    # =========================================================================
    print("=" * 60)
    print("Step 1: Building DB post index...")
    print("=" * 60)

    db_posts = conn.execute('''
        SELECT p.post_id, pg.page_name, p.publish_time, p.views_count, p.reach_count
        FROM posts p JOIN pages pg ON p.page_id = pg.page_id
        WHERE p.publish_time IS NOT NULL AND p.post_id NOT LIKE '%E+%'
    ''').fetchall()

    # Index with 2-minute tolerance window
    db_index = {}  # (page_name_lower, "YYYY-MM-DD HH:MM") -> [(post_id, views, reach)]
    for post_id, page_name, pub_time, views, reach in db_posts:
        dt = parse_time(pub_time)
        if dt:
            pname = page_name.lower().strip()
            for offset_min in range(-2, 3):
                dt2 = dt + timedelta(minutes=offset_min)
                key = (pname, dt2.strftime('%Y-%m-%d %H:%M'))
                if key not in db_index:
                    db_index[key] = []
                db_index[key].append((post_id, views or 0, reach or 0))

    print(f"  DB posts indexed: {len(db_posts)} (excluding E+ IDs)")

    # =========================================================================
    # STEP 2: Load and match CSV rows
    # =========================================================================
    print("\nStep 2: Loading CSV and matching...")

    with open(CSV_PATH, 'r', encoding='utf-8-sig') as f:
        reader = csv.reader(f)
        header = next(reader)
        rows = list(reader)

    print(f"  CSV rows: {len(rows)}")

    # Match and collect updates
    updates = []  # (post_id, views, reach)
    matched = 0
    unmatched = 0
    already_matched = set()  # Avoid double-matching

    for row in rows:
        csv_page_name = row[2].strip()
        csv_pub_time = row[6]
        csv_views = int(row[17]) if row[17] else 0
        csv_reach = int(row[18]) if row[18] else 0

        dt = parse_time(csv_pub_time)
        if dt:
            # CSV is UTC, DB is PHT (stored as +0000)
            dt_pht = dt + PHT_OFFSET
            key = (csv_page_name.lower().strip(), dt_pht.strftime('%Y-%m-%d %H:%M'))

            if key in db_index:
                # Find unmatched post_id from this key
                found = False
                for post_id, db_views, db_reach in db_index[key]:
                    if post_id not in already_matched:
                        updates.append((csv_views, csv_reach, post_id))
                        already_matched.add(post_id)
                        matched += 1
                        found = True
                        break
                if not found:
                    unmatched += 1
            else:
                unmatched += 1
        else:
            unmatched += 1

    print(f"  Matched: {matched}")
    print(f"  Unmatched: {unmatched}")

    # =========================================================================
    # STEP 3: Apply views/reach updates
    # =========================================================================
    print(f"\nStep 3: Updating views/reach for {len(updates)} posts...")

    updated_views = 0
    for csv_views, csv_reach, post_id in updates:
        conn.execute('''
            UPDATE posts SET views_count = ?, reach_count = ?
            WHERE post_id = ?
        ''', (csv_views, csv_reach, post_id))
        updated_views += 1

    conn.commit()
    print(f"  Updated: {updated_views} posts")

    # =========================================================================
    # STEP 4: Clean up E+ duplicate posts
    # =========================================================================
    print("\nStep 4: Cleaning up E+ duplicate posts...")

    e_plus_count = conn.execute(
        "SELECT COUNT(*) FROM posts WHERE post_id LIKE '%E+%'"
    ).fetchone()[0]
    print(f"  E+ posts found: {e_plus_count}")

    if e_plus_count > 0:
        # Delete E+ posts
        conn.execute("DELETE FROM posts WHERE post_id LIKE '%E+%'")
        # Also clean post_metrics
        conn.execute("DELETE FROM post_metrics WHERE post_id LIKE '%E+%'")
        conn.commit()
        print(f"  Deleted: {e_plus_count} E+ posts")

    # =========================================================================
    # STEP 5: Verify results
    # =========================================================================
    print("\n" + "=" * 60)
    print("Step 5: Verification")
    print("=" * 60)

    total = conn.execute("SELECT COUNT(*) FROM posts").fetchone()[0]
    with_views = conn.execute(
        "SELECT COUNT(*) FROM posts WHERE views_count > 0"
    ).fetchone()[0]
    no_views = conn.execute(
        "SELECT COUNT(*) FROM posts WHERE views_count = 0 OR views_count IS NULL"
    ).fetchone()[0]

    print(f"  Total posts: {total}")
    print(f"  Posts with views: {with_views}")
    print(f"  Posts without views: {no_views}")

    # Check Feb data
    print("\n  Feb 2026 daily summary:")
    for r in conn.execute('''
        SELECT
            substr(publish_time, 1, 10) as pub_date,
            COUNT(*) as posts,
            SUM(COALESCE(views_count, 0)) as views,
            SUM(COALESCE(reach_count, 0)) as reach,
            SUM(COALESCE(reactions_total, 0)) as reactions
        FROM posts
        WHERE publish_time >= '2026-02-01'
        GROUP BY pub_date
        ORDER BY pub_date
    '''):
        flag = " <-- was 0" if r[0] >= '2026-02-09' and r[2] > 0 else ""
        print(f"    {r[0]}: {r[1]} posts, views={r[2]:,}, reach={r[3]:,}, reactions={r[4]:,}{flag}")

    conn.close()
    print("\nDone! Run 'python export_static_data.py' to update the dashboard.")


if __name__ == '__main__':
    main()
