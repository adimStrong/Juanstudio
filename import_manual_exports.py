#!/usr/bin/env python3
"""Import manually exported CSV files from Meta Business Suite.

IMPORTANT: Meta CSV exports have Post IDs in scientific notation (e.g. 1.22187E+17)
which causes precision loss — converting gives wrong IDs like 122187000000000000.
1,718 rows can collapse to just 228 unique (wrong) IDs.

Strategy: IGNORE the CSV Post ID entirely. Instead, match CSV rows to existing
DB posts by (page_id + publish_time). Only UPDATE views/reach on matched posts.
Posts not already in DB (from API fetch) are skipped — API is the source of truth
for post identity, CSV is only for views/reach data.
"""

import csv
import sqlite3
import os
from datetime import datetime, timedelta
from glob import glob

# Import database function for duplicate prevention
try:
    from database import get_page_by_name
except ImportError:
    get_page_by_name = None

DATABASE_PATH = "data/juanstudio_analytics.db"
EXPORTS_FOLDER = "exports/from content manual Export"

# Track page_id remapping (CSV ID -> existing DB ID)
page_id_remap = {}


def get_conn():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def parse_datetime_to_api_format(dt_str):
    """Parse CSV datetime (MM/DD/YYYY HH:MM) to match DB format.

    CSV exports UTC times. DB stores API times as ISO+0000 which are
    offset by +8h from CSV (API returns PHT labeled as +0000).
    So: CSV_time + 8h = DB_time (verified by title-matching posts).
    """
    if not dt_str:
        return None, None
    try:
        dt = datetime.strptime(dt_str.strip(), "%m/%d/%Y %H:%M")
        # Add 8 hours to match DB time format (CSV UTC -> DB PHT-as-UTC)
        dt_adjusted = dt + timedelta(hours=8)
        iso = dt_adjusted.isoformat()
        return iso, dt_adjusted
    except:
        return dt_str, None


def safe_int(val):
    """Safely convert to int."""
    if not val or val == "":
        return 0
    try:
        return int(float(val))
    except:
        return 0


def import_csv(filepath):
    """Import a single CSV file by matching to existing DB posts."""
    global page_id_remap
    print(f"\nImporting: {os.path.basename(filepath)}")

    conn = get_conn()
    cursor = conn.cursor()

    updated = 0
    skipped = 0
    not_found = 0
    pages_seen = set()

    with open(filepath, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)

        for row in reader:
            csv_page_id = row.get("Page ID", "")
            page_name = row.get("Page name", "")
            post_id_raw = row.get("Post ID", "")

            if not post_id_raw or not csv_page_id:
                skipped += 1
                continue

            # Resolve page_id (CSV may use different ID than API)
            if csv_page_id in page_id_remap:
                page_id = page_id_remap[csv_page_id]
            elif get_page_by_name:
                existing_page = get_page_by_name(page_name, conn=conn)
                if existing_page and existing_page["page_id"] != csv_page_id:
                    page_id = existing_page["page_id"]
                    page_id_remap[csv_page_id] = page_id
                else:
                    page_id = csv_page_id
                    page_id_remap[csv_page_id] = csv_page_id
            else:
                page_id = csv_page_id

            pages_seen.add(page_id)

            # Parse CSV data
            publish_time_str = row.get("Publish time", "")
            publish_time, dt_obj = parse_datetime_to_api_format(publish_time_str)
            if not publish_time:
                skipped += 1
                continue

            views = safe_int(row.get("Views", 0))
            reach = safe_int(row.get("Reach", 0))
            reactions = safe_int(row.get("Reactions", 0))
            comments = safe_int(row.get("Comments", 0))
            shares = safe_int(row.get("Shares", 0))

            # Match to existing DB post by page_id + publish_time
            # API stores times like: 2026-02-01T00:00:16+0000
            # CSV times (after parse): 2026-02-01T00:00:00
            # Match by truncating to minute (first 16 chars: 2026-02-01T00:00)
            time_prefix = publish_time[:16] if publish_time else ""

            cursor.execute("""
                SELECT post_id FROM posts
                WHERE page_id = ? AND SUBSTR(publish_time, 1, 16) = ?
                LIMIT 1
            """, (page_id, time_prefix))
            match = cursor.fetchone()

            if match:
                matched_post_id = match[0]
                # Update views/reach and engagement on the matched post
                total_engagement = reactions + comments + shares
                pes = (reactions * 1.0) + (comments * 2.0) + (shares * 3.0)

                cursor.execute("""
                    UPDATE posts SET
                        views_count = MAX(COALESCE(views_count, 0), ?),
                        reach_count = MAX(COALESCE(reach_count, 0), ?),
                        reactions_total = MAX(COALESCE(reactions_total, 0), ?),
                        comments_count = MAX(COALESCE(comments_count, 0), ?),
                        shares_count = MAX(COALESCE(shares_count, 0), ?),
                        total_engagement = MAX(COALESCE(total_engagement, 0), ?),
                        pes = MAX(COALESCE(pes, 0), ?)
                    WHERE post_id = ?
                """, (views, reach, reactions, comments, shares,
                      total_engagement, pes, matched_post_id))
                updated += 1
            else:
                not_found += 1

    conn.commit()
    conn.close()

    print(f"  Updated {updated} posts with views/reach data")
    if not_found > 0:
        print(f"  {not_found} CSV rows had no matching DB post (not yet fetched via API)")
    if skipped > 0:
        print(f"  {skipped} rows skipped (missing data)")
    return updated, pages_seen


def main():
    global page_id_remap
    page_id_remap = {}

    print("=" * 60)
    print("Importing Manual CSV Exports (views/reach update only)")
    print("=" * 60)

    csv_files = glob(os.path.join(EXPORTS_FOLDER, "*.csv"))

    if not csv_files:
        print(f"No CSV files found in {EXPORTS_FOLDER}")
        return

    print(f"Found {len(csv_files)} CSV files")

    total_updated = 0
    all_pages = set()

    for csv_file in sorted(csv_files):
        count, pages = import_csv(csv_file)
        total_updated += count
        all_pages.update(pages)

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Total posts updated: {total_updated}")
    print(f"Total pages: {len(all_pages)}")

    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT p.page_name, COUNT(po.post_id) as post_count,
               SUM(po.reactions_total) as total_reactions,
               SUM(po.views_count) as total_views,
               SUM(po.reach_count) as total_reach
        FROM pages p
        LEFT JOIN posts po ON p.page_id = po.page_id
        GROUP BY p.page_id
        ORDER BY post_count DESC
    """)

    print("\nPage breakdown:")
    for row in cursor.fetchall():
        name, posts, reactions, views, reach = row
        print(f"  {name}: {posts} posts, {reactions or 0} reactions, {views or 0} views")

    conn.close()


if __name__ == "__main__":
    main()
