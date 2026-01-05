#!/usr/bin/env python3
"""
One-time script to clean up duplicate posts caused by different ID formats.

API format: pageId_postId (e.g., 862622980275034_123456789)
CSV format: postId only (e.g., 123456789)

This script normalizes all post IDs to the short format.
"""

import sqlite3

DATABASE_PATH = "data/juanstudio_analytics.db"


def normalize_post_id(post_id: str) -> str:
    """Extract pure post ID, stripping page ID prefix if present."""
    post_id_str = str(post_id)
    if '_' in post_id_str:
        return post_id_str.split('_')[-1]
    return post_id_str


def cleanup_duplicates():
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    # Find all posts with underscore in ID (API format)
    cursor.execute("""
        SELECT post_id FROM posts
        WHERE post_id LIKE '%_%'
    """)
    long_ids = cursor.fetchall()

    print(f"Found {len(long_ids)} posts with long format IDs (pageId_postId)")

    deleted = 0
    renamed = 0

    for (long_id,) in long_ids:
        short_id = normalize_post_id(long_id)

        # Check if short version already exists
        cursor.execute("SELECT 1 FROM posts WHERE post_id = ?", (short_id,))
        if cursor.fetchone():
            # Delete the long version (it's a duplicate)
            cursor.execute("DELETE FROM posts WHERE post_id = ?", (long_id,))
            deleted += 1
        else:
            # Rename long to short
            cursor.execute("UPDATE posts SET post_id = ? WHERE post_id = ?", (short_id, long_id))
            renamed += 1

    # Also clean up post_metrics if any
    cursor.execute("""
        SELECT DISTINCT post_id FROM post_metrics
        WHERE post_id LIKE '%_%'
    """)
    long_metric_ids = cursor.fetchall()

    metrics_updated = 0
    for (long_id,) in long_metric_ids:
        short_id = normalize_post_id(long_id)
        cursor.execute("UPDATE post_metrics SET post_id = ? WHERE post_id = ?", (short_id, long_id))
        metrics_updated += cursor.rowcount

    conn.commit()

    # Get final counts
    cursor.execute("SELECT COUNT(*) FROM posts")
    total_posts = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM posts WHERE post_id LIKE '%_%'")
    remaining_long = cursor.fetchone()[0]

    conn.close()

    print(f"\nCleanup Summary:")
    print(f"  - Deleted (duplicates): {deleted}")
    print(f"  - Renamed (normalized): {renamed}")
    print(f"  - Metrics updated: {metrics_updated}")
    print(f"  - Total posts now: {total_posts}")
    print(f"  - Remaining long IDs: {remaining_long}")

    if remaining_long == 0:
        print("\n✓ All post IDs are now normalized!")
    else:
        print(f"\n⚠ Warning: {remaining_long} posts still have long format IDs")


if __name__ == "__main__":
    print("=" * 60)
    print("JuanStudio - Cleanup Duplicate Post IDs")
    print("=" * 60)
    cleanup_duplicates()
