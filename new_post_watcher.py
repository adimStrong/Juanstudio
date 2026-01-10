"""
JuanStudio New Post Watcher
Checks for new posts every hour and sends Telegram notifications

Usage:
    python new_post_watcher.py              # Run once (for Task Scheduler)
    python new_post_watcher.py --daemon     # Run as background daemon
    pythonw new_post_watcher.py --daemon    # Run hidden (no window)
"""

import sqlite3
import subprocess
import sys
import time
import json
from datetime import datetime, timedelta
from pathlib import Path

PROJECT_DIR = Path(__file__).parent
DB_PATH = PROJECT_DIR / "data" / "juanstudio_analytics.db"
STATE_FILE = PROJECT_DIR / "data" / "watcher_state.json"
CHECK_INTERVAL = 3600  # 1 hour in seconds

def log(msg, level="INFO"):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] [{level}] {msg}")

def load_state():
    """Load last notified post IDs."""
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE, 'r') as f:
                return json.load(f)
        except:
            pass
    return {"last_check": None, "notified_posts": []}

def save_state(state):
    """Save state to file."""
    STATE_FILE.parent.mkdir(exist_ok=True)
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)

def fetch_new_posts_from_api():
    """Fetch last 7 days from Facebook API."""
    log("Fetching from Facebook API...")
    try:
        result = subprocess.run(
            [sys.executable, "fetch_missing_posts.py"],
            cwd=PROJECT_DIR,
            capture_output=True,
            text=True,
            timeout=300
        )
        if "Added" in result.stdout:
            # Extract number of new posts
            for line in result.stdout.split('\n'):
                if "Added" in line and "new posts" in line:
                    log(line.strip())
                    return True
        return False
    except Exception as e:
        log(f"API fetch error: {e}", "ERROR")
        return False

def get_recent_posts(hours=2):
    """Get posts PUBLISHED in the last N hours (not fetched)."""
    if not DB_PATH.exists():
        return []

    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Facebook API returns UTC time (+0000), so convert local time to UTC for comparison
    # Philippines is UTC+8, so subtract 8 hours from local time
    local_now = datetime.now()
    utc_now = local_now - timedelta(hours=8)  # Convert to UTC
    since_time_utc = (utc_now - timedelta(hours=hours)).strftime('%Y-%m-%dT%H:%M:%S')

    cursor.execute("""
        SELECT
            posts.post_id,
            p.page_name,
            posts.post_type,
            posts.title,
            posts.permalink,
            posts.publish_time,
            posts.created_at,
            posts.fetched_at
        FROM posts
        JOIN pages p ON posts.page_id = p.page_id
        WHERE posts.publish_time >= ?
        ORDER BY posts.publish_time DESC
    """, (since_time_utc,))

    posts = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return posts

def notify_new_posts(posts, state):
    """Send Telegram notifications for new posts."""
    from telegram_notifier import send_new_post_alert

    notified = state.get("notified_posts", [])
    new_notifications = 0

    for post in posts:
        post_id = post['post_id']

        # Skip if already notified
        if post_id in notified:
            continue

        log(f"Notifying: {post['page_name']} - {post['post_type']}")

        result = send_new_post_alert(
            page_name=post['page_name'],
            post_type=post['post_type'],
            title=post['title'],
            permalink=post['permalink'],
            publish_time=post['publish_time']
        )

        if result and result.get('ok'):
            notified.append(post_id)
            new_notifications += 1
            time.sleep(1)  # Rate limit

    # Keep only last 500 notified IDs to prevent file bloat
    state["notified_posts"] = notified[-500:]

    return new_notifications

def check_for_new_posts():
    """Main check function - fetch API and notify."""
    log("=" * 50)
    log("Checking for new posts...")

    state = load_state()

    # Fetch from API
    fetch_new_posts_from_api()

    # Get posts PUBLISHED in the last 2 hours
    recent_posts = get_recent_posts(hours=2)

    if not recent_posts:
        log("No new posts found")
        state["last_check"] = datetime.now().isoformat()
        save_state(state)
        return 0

    log(f"Found {len(recent_posts)} recent posts, checking for new notifications...")

    # Send notifications
    new_count = notify_new_posts(recent_posts, state)

    state["last_check"] = datetime.now().isoformat()
    save_state(state)

    if new_count > 0:
        log(f"Sent {new_count} new notification(s)")
    else:
        log("All posts already notified")

    return new_count

def run_daemon():
    """Run as background daemon, checking every hour."""
    log("=" * 50)
    log("JuanStudio New Post Watcher - DAEMON MODE")
    log(f"Checking every {CHECK_INTERVAL // 60} minutes")
    log("=" * 50)

    while True:
        try:
            check_for_new_posts()
        except Exception as e:
            log(f"Error during check: {e}", "ERROR")

        # Calculate next check time
        next_check = datetime.now() + timedelta(seconds=CHECK_INTERVAL)
        log(f"Next check at: {next_check.strftime('%H:%M:%S')}")
        log("-" * 50)

        time.sleep(CHECK_INTERVAL)

def main():
    import argparse
    parser = argparse.ArgumentParser(description="JuanStudio New Post Watcher")
    parser.add_argument("--daemon", action="store_true", help="Run as background daemon")
    args = parser.parse_args()

    if args.daemon:
        run_daemon()
    else:
        # Single check (for Task Scheduler)
        check_for_new_posts()

if __name__ == "__main__":
    main()
