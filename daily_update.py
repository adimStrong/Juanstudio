"""
JuanStudio Daily Update Script
Combines API fetch + CSV import + export in one command

Usage:
    python daily_update.py              # Run all steps
    python daily_update.py --api-only   # Only fetch from API
    python daily_update.py --csv-only   # Only import CSVs
    python daily_update.py --export     # Only export static data
    python daily_update.py --notify     # Send Telegram notification for new posts
"""

import subprocess
import sys
import argparse
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

PROJECT_DIR = Path(__file__).parent
DB_PATH = PROJECT_DIR / "data" / "juanstudio_analytics.db"

def log(msg, level="INFO"):
    timestamp = datetime.now().strftime('%H:%M:%S')
    print(f"[{timestamp}] [{level}] {msg}")

def get_new_posts_since(minutes=30):
    """Get posts added in the last N minutes."""
    if not DB_PATH.exists():
        return []

    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Get posts fetched recently (by fetched_at or created_at)
    since_time = (datetime.now() - timedelta(minutes=minutes)).strftime('%Y-%m-%d %H:%M:%S')

    cursor.execute("""
        SELECT
            p.page_name,
            posts.post_type,
            posts.title,
            posts.permalink,
            posts.publish_time
        FROM posts
        JOIN pages p ON posts.page_id = p.page_id
        WHERE posts.created_at >= ? OR posts.fetched_at >= ?
        ORDER BY posts.publish_time DESC
    """, (since_time, since_time))

    posts = cursor.fetchall()
    conn.close()
    return posts

def notify_new_posts():
    """Send Telegram notifications for new posts."""
    try:
        from telegram_notifier import send_new_post_alert

        new_posts = get_new_posts_since(minutes=60)  # Posts added in last hour

        if not new_posts:
            log("No new posts to notify")
            return 0

        log(f"Sending {len(new_posts)} new post notification(s)...")
        sent = 0
        for post in new_posts:
            result = send_new_post_alert(
                page_name=post['page_name'],
                post_type=post['post_type'],
                title=post['title'],
                permalink=post['permalink'],
                publish_time=post['publish_time']
            )
            if result and result.get('ok'):
                sent += 1

        log(f"Sent {sent}/{len(new_posts)} notifications")
        return sent
    except ImportError:
        log("telegram_notifier not available", "WARN")
        return 0
    except Exception as e:
        log(f"Notification error: {e}", "ERROR")
        return 0

def run_step(name, cmd, required=True):
    """Run a command and return success status"""
    log(f"Starting: {name}")
    try:
        result = subprocess.run(
            cmd,
            cwd=PROJECT_DIR,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        if result.returncode != 0:
            if required:
                log(f"FAILED: {name}", "ERROR")
                if result.stderr:
                    print(f"    Error: {result.stderr[:500]}")
                return False
            else:
                log(f"Warning in {name}: {result.stderr[:200] if result.stderr else 'Unknown'}", "WARN")
        else:
            log(f"Completed: {name}")
            # Show summary if available
            if result.stdout:
                for line in result.stdout.split('\n')[-5:]:
                    if line.strip():
                        print(f"    {line.strip()}")
        return True
    except subprocess.TimeoutExpired:
        log(f"TIMEOUT: {name} (exceeded 5 minutes)", "ERROR")
        return False
    except Exception as e:
        log(f"EXCEPTION in {name}: {e}", "ERROR")
        return False

def fetch_api():
    """Fetch last 7 days from Facebook API"""
    return run_step(
        "Fetch API data (7 days)",
        [sys.executable, "fetch_missing_posts.py"],
        required=False  # Don't fail if API has issues
    )

def import_csv():
    """Import any new CSV files"""
    return run_step(
        "Import new CSVs",
        [sys.executable, "csv_importer.py", "find"],
        required=False
    )

def export_data():
    """Export static JSON for frontend"""
    return run_step(
        "Export static data",
        [sys.executable, "export_static_data.py"],
        required=True
    )

def copy_to_frontend():
    """Copy analytics-v2.json to analytics.json"""
    src = PROJECT_DIR / "frontend" / "public" / "data" / "analytics-v2.json"
    dst = PROJECT_DIR / "frontend" / "public" / "data" / "analytics.json"
    if src.exists():
        import shutil
        shutil.copy(src, dst)
        log("Copied analytics-v2.json -> analytics.json")
        return True
    return False

def main():
    parser = argparse.ArgumentParser(description="JuanStudio Daily Update")
    parser.add_argument("--api-only", action="store_true", help="Only fetch from API")
    parser.add_argument("--csv-only", action="store_true", help="Only import CSVs")
    parser.add_argument("--export", action="store_true", help="Only export static data")
    parser.add_argument("--notify", action="store_true", help="Send Telegram notifications for new posts")
    parser.add_argument("--no-notify", action="store_true", help="Skip Telegram notifications")
    args = parser.parse_args()

    print("=" * 60)
    print("JUANSTUDIO DAILY UPDATE")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    results = []

    if args.notify:
        # Only send notifications
        sent = notify_new_posts()
        results.append(("Telegram Notify", sent > 0 or True))
    elif args.api_only:
        results.append(("API Fetch", fetch_api()))
    elif args.csv_only:
        results.append(("CSV Import", import_csv()))
    elif args.export:
        results.append(("Export", export_data()))
        copy_to_frontend()
    else:
        # Run all steps
        results.append(("API Fetch", fetch_api()))
        results.append(("CSV Import", import_csv()))
        results.append(("Export", export_data()))
        copy_to_frontend()

        # Send notifications for new posts (unless --no-notify)
        if not args.no_notify:
            print("\n" + "-" * 40)
            sent = notify_new_posts()
            results.append(("Telegram Notify", True))

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    success = sum(1 for _, ok in results if ok)
    total = len(results)

    for name, ok in results:
        status = "OK" if ok else "FAILED"
        print(f"  {name}: {status}")

    print(f"\nCompleted: {success}/{total} steps successful")
    print(f"Finished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    return 0 if success == total else 1

if __name__ == "__main__":
    sys.exit(main())
