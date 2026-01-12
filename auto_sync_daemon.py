"""
JuanStudio Auto Sync Daemon
Runs in background and syncs at 6:00 AM daily

This daemon performs FULL sync including:
1. Posts sync (from Facebook API - last 30 days)
2. Follower counts update
3. Comment data fetch (self-comments vs organic)
4. CSV import (if new files exist)
5. Export static data

Usage:
    python auto_sync_daemon.py          # Run in foreground
    pythonw auto_sync_daemon.py         # Run hidden (no window)
    python auto_sync_daemon.py --now    # Run sync immediately

To auto-start on login:
    1. Press Win+R, type: shell:startup
    2. Create shortcut to: pythonw auto_sync_daemon.py
"""

import subprocess
import time
import os
import sys
from datetime import datetime, timedelta

PROJECT_DIR = r"C:\Users\us\Desktop\juanstudio_project"
SYNC_HOUR = 6  # 6 AM
SYNC_MINUTE = 0
SYNC_DAYS = 30  # Fetch last 30 days of posts (not just 7)

def show_notification(title, message):
    """Show Windows notification"""
    try:
        ps_command = f"Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.MessageBox]::Show('{message}', '{title}', 'OK', 'Information')"
        subprocess.run(['powershell', '-Command', ps_command], capture_output=True)
    except:
        print(f"[NOTIFY] {title}: {message}")

def run_sync():
    """Run the FULL API sync including posts, followers, and comments"""
    os.chdir(PROJECT_DIR)
    print(f"\n{'='*60}")
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Starting FULL sync...")
    print('='*60)

    try:
        # Step 1: Fetch posts from Facebook API (last 30 days)
        print("\n[1/6] Fetching posts from Facebook API (last 30 days)...")
        if os.path.exists('fetch_missing_posts.py'):
            result = subprocess.run([sys.executable, 'fetch_missing_posts.py'], capture_output=True, text=True)
            if result.returncode != 0:
                print(f"   Warning: {result.stderr[:200] if result.stderr else 'Unknown error'}")
            else:
                print("   API fetch complete")
        elif os.path.exists('scheduled_sync.py'):
            subprocess.run([sys.executable, 'scheduled_sync.py'], check=True)
        else:
            print("   (No post fetcher found, skipping)")

        # Step 2: Update follower counts
        print("\n[2/6] Updating follower counts...")
        if os.path.exists('update_followers.py'):
            subprocess.run([sys.executable, 'update_followers.py'], check=True)
        else:
            print("   (update_followers.py not found, skipping)")

        # Step 3: Fetch comment data
        print("\n[3/6] Fetching comment data (self-comments)...")
        if os.path.exists('fetch_comments.py'):
            subprocess.run([sys.executable, 'fetch_comments.py'], check=True)
        else:
            print("   (fetch_comments.py not found, skipping)")

        # Step 4: Check for new CSV files
        print("\n[4/6] Checking for new CSV exports...")
        if os.path.exists('csv_importer.py'):
            result = subprocess.run([sys.executable, 'csv_importer.py', 'find'], capture_output=True, text=True)
            if "No new CSV" in result.stdout:
                print("   No new CSV files found")
            else:
                print("   CSV import complete")
        else:
            print("   (csv_importer.py not found, skipping)")

        # Step 5: Export static data
        print("\n[5/6] Exporting analytics data...")
        if os.path.exists('export_static_data.py'):
            subprocess.run([sys.executable, 'export_static_data.py'], check=True, capture_output=True)
            print("   Export complete")
        else:
            print("   (export_static_data.py not found, skipping)")

        # Step 6: Send notifications
        print("\n[6/6] Sending Telegram notifications...")
        if os.path.exists('send_daily_report.py'):
            result = subprocess.run([sys.executable, 'send_daily_report.py'], capture_output=True, text=True)
            print("   Notifications sent")
        else:
            print("   (send_daily_report.py not found, skipping)")

        show_notification("JuanStudio Daily Sync", "Full sync complete!")

        print(f"\n{'='*60}")
        print(f"[{datetime.now().strftime('%H:%M:%S')}] FULL SYNC COMPLETE!")
        print('='*60)

    except Exception as e:
        print(f"\nError during sync: {e}")
        show_notification("JuanStudio Sync Error", str(e)[:100])

def get_seconds_until_next_sync():
    """Calculate seconds until next sync time"""
    now = datetime.now()
    target = now.replace(hour=SYNC_HOUR, minute=SYNC_MINUTE, second=0, microsecond=0)

    if now >= target:
        target += timedelta(days=1)

    return (target - now).total_seconds()

def main():
    # Check for --now flag to run immediately
    if "--now" in sys.argv:
        print("Running sync immediately...")
        run_sync()
        return

    print("="*60)
    print("JuanStudio Auto Sync Daemon")
    print("="*60)
    print(f"Project: {PROJECT_DIR}")
    print(f"Sync scheduled for: {SYNC_HOUR:02d}:{SYNC_MINUTE:02d} daily")
    print(f"Tasks: Posts + Followers + Comments + CSV + Export")
    print("Press Ctrl+C to stop")
    print("="*60)

    show_notification("JuanStudio Daemon Started", f"Will sync daily at {SYNC_HOUR}:00 AM")

    last_sync_date = None

    while True:
        now = datetime.now()
        today = now.date()

        # Check if it's sync time and we haven't synced today
        if now.hour == SYNC_HOUR and now.minute == SYNC_MINUTE and last_sync_date != today:
            run_sync()
            last_sync_date = today

        # Sleep for 30 seconds before checking again
        time.sleep(30)

if __name__ == "__main__":
    main()
