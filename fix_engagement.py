#!/usr/bin/env python3
"""
Fix engagement: Update reactions/comments/shares from CSV where CSV has higher values.
CSV has lifetime cumulative metrics which are more accurate than point-in-time API fetches.
"""

import csv
import sqlite3
from datetime import datetime, timedelta

CSV_PATH = r"exports\from content manual Export\Dec-31-2025_Feb-11-2026_1460887702334520.csv"
DB_PATH = r"data\juanstudio_analytics.db"
PHT_OFFSET = timedelta(hours=8)


def parse_time(t):
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


def safe_int(v):
    if not v or v == 'N/A':
        return 0
    try:
        return int(float(str(v).replace(',', '').strip()))
    except (ValueError, TypeError):
        return 0


def main():
    conn = sqlite3.connect(DB_PATH)

    # Build DB index
    print("Building DB index...")
    db_posts = conn.execute('''
        SELECT p.post_id, pg.page_name, p.publish_time,
               p.reactions_total, p.comments_count, p.shares_count,
               p.views_count, p.reach_count
        FROM posts p JOIN pages pg ON p.page_id = pg.page_id
        WHERE p.publish_time IS NOT NULL
    ''').fetchall()

    db_index = {}
    for post_id, page_name, pub_time, reactions, comments, shares, views, reach in db_posts:
        dt = parse_time(pub_time)
        if dt:
            pname = page_name.lower().strip()
            for offset_min in range(-2, 3):
                dt2 = dt + timedelta(minutes=offset_min)
                key = (pname, dt2.strftime('%Y-%m-%d %H:%M'))
                if key not in db_index:
                    db_index[key] = []
                db_index[key].append({
                    'post_id': post_id,
                    'reactions': reactions or 0,
                    'comments': comments or 0,
                    'shares': shares or 0,
                    'views': views or 0,
                    'reach': reach or 0,
                })

    print(f"  Indexed {len(db_posts)} posts")

    # Load CSV
    with open(CSV_PATH, 'r', encoding='utf-8-sig') as f:
        reader = csv.reader(f)
        header = next(reader)
        rows = list(reader)

    print(f"  CSV rows: {len(rows)}")

    # Match and update - take MAX of CSV vs DB for each metric
    matched = 0
    updated = 0
    already_matched = set()

    for row in rows:
        csv_page_name = row[2].strip()
        csv_pub_time = row[6]
        csv_reactions = safe_int(row[20])
        csv_comments = safe_int(row[21])
        csv_shares = safe_int(row[22])
        csv_views = safe_int(row[17])
        csv_reach = safe_int(row[18])

        dt = parse_time(csv_pub_time)
        if not dt:
            continue

        dt_pht = dt + PHT_OFFSET
        key = (csv_page_name.lower().strip(), dt_pht.strftime('%Y-%m-%d %H:%M'))

        if key not in db_index:
            continue

        for db_post in db_index[key]:
            post_id = db_post['post_id']
            if post_id in already_matched:
                continue

            # Take the MAX of CSV vs DB for each metric
            new_reactions = max(csv_reactions, db_post['reactions'])
            new_comments = max(csv_comments, db_post['comments'])
            new_shares = max(csv_shares, db_post['shares'])
            new_views = max(csv_views, db_post['views'])
            new_reach = max(csv_reach, db_post['reach'])
            new_engagement = new_reactions + new_comments + new_shares

            # Check if any value actually changed
            changed = (
                new_reactions != db_post['reactions'] or
                new_comments != db_post['comments'] or
                new_shares != db_post['shares'] or
                new_views != db_post['views'] or
                new_reach != db_post['reach']
            )

            if changed:
                conn.execute('''
                    UPDATE posts SET
                        reactions_total = ?,
                        comments_count = ?,
                        shares_count = ?,
                        views_count = ?,
                        reach_count = ?,
                        total_engagement = ?
                    WHERE post_id = ?
                ''', (new_reactions, new_comments, new_shares, new_views, new_reach, new_engagement, post_id))
                updated += 1

            already_matched.add(post_id)
            matched += 1
            break

    conn.commit()

    print(f"\n  Matched: {matched}")
    print(f"  Updated (higher values): {updated}")

    # Verify
    print("\n=== Feb 2026 daily summary (after fix) ===")
    for r in conn.execute('''
        SELECT substr(publish_time, 1, 10) as pub_date,
            COUNT(*) as posts,
            SUM(COALESCE(reactions_total, 0)) as reactions,
            SUM(COALESCE(comments_count, 0)) as comments,
            SUM(COALESCE(shares_count, 0)) as shares,
            SUM(COALESCE(total_engagement, 0)) as engagement,
            SUM(COALESCE(views_count, 0)) as views,
            SUM(COALESCE(reach_count, 0)) as reach
        FROM posts WHERE publish_time >= '2026-02-01'
        GROUP BY pub_date ORDER BY pub_date
    '''):
        print(f'  {r[0]}: {r[1]}p react={r[2]:,} cmts={r[3]:,} shares={r[4]:,} eng={r[5]:,} views={r[6]:,} reach={r[7]:,}')

    # Overall totals
    r = conn.execute('''
        SELECT SUM(reactions_total), SUM(comments_count), SUM(shares_count), SUM(total_engagement),
               SUM(views_count), SUM(reach_count)
        FROM posts WHERE reactions_total > 0 OR comments_count > 0 OR shares_count > 0
    ''').fetchone()
    print(f'\n=== Overall totals ===')
    print(f'  Reactions: {r[0]:,}')
    print(f'  Comments: {r[1]:,}')
    print(f'  Shares: {r[2]:,}')
    print(f'  Engagement: {r[3]:,}')
    print(f'  Views: {r[4]:,}')
    print(f'  Reach: {r[5]:,}')

    conn.close()
    print("\nDone!")


if __name__ == '__main__':
    main()
