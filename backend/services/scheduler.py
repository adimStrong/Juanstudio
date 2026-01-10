"""Background task scheduler for automated reporting."""

from datetime import datetime
from typing import Optional

# Optional APScheduler support
scheduler = None


def start_scheduler():
    """Start the background scheduler."""
    global scheduler

    try:
        from apscheduler.schedulers.asyncio import AsyncIOScheduler
        from apscheduler.triggers.cron import CronTrigger

        scheduler = AsyncIOScheduler()

        # Daily report at 8:00 AM
        scheduler.add_job(
            send_daily_report,
            CronTrigger(hour=8, minute=0),
            id="daily_report",
            name="Send daily Telegram report",
            replace_existing=True,
        )

        # Token expiry check at 9:00 AM
        scheduler.add_job(
            check_token_expiry,
            CronTrigger(hour=9, minute=0),
            id="token_check",
            name="Check token expiry",
            replace_existing=True,
        )

        scheduler.start()
        print("Scheduler started - Daily report at 8:00 AM")

    except ImportError:
        print("APScheduler not installed - scheduler disabled")
        print("Install with: pip install apscheduler")


def stop_scheduler():
    """Stop the background scheduler."""
    global scheduler
    if scheduler:
        scheduler.shutdown()
        print("Scheduler stopped")


async def send_daily_report():
    """Send the daily Telegram report."""
    print(f"[{datetime.now()}] Running daily report...")

    try:
        from fb_analytics_core.reports import DailyReportGenerator
        from fb_analytics_core.ai import InsightsGenerator
        from fb_analytics_core.notifications import TelegramNotifier

        DATABASE_PATH = "data/juanstudio_analytics.db"

        generator = DailyReportGenerator(DATABASE_PATH)
        report_data = generator.generate_report_data()

        # Generate AI insight
        try:
            insights = InsightsGenerator()
            ai_insight = await insights.generate_daily_insight(
                report_data["stats"],
                report_data.get("top_posts", [])
            )
        except Exception as e:
            print(f"AI insight error: {e}")
            ai_insight = None

        # Format and send
        message = generator.format_telegram_message(report_data, ai_insight)

        notifier = TelegramNotifier()
        result = await notifier.send(message)

        if result.get("ok"):
            print(f"[{datetime.now()}] Daily report sent successfully")
        else:
            print(f"[{datetime.now()}] Failed to send report: {result}")

    except Exception as e:
        print(f"[{datetime.now()}] Daily report error: {e}")


async def check_token_expiry():
    """Check Facebook token expiry and send alerts."""
    print(f"[{datetime.now()}] Checking token expiry...")

    try:
        import json
        from pathlib import Path
        from fb_analytics_core.facebook import TokenManager
        from fb_analytics_core.notifications import TelegramNotifier

        tokens_file = Path("page_tokens.json")
        if not tokens_file.exists():
            print("No page_tokens.json found")
            return

        with open(tokens_file) as f:
            tokens = json.load(f)

        token_list = [
            {
                "page_id": data.get("page_id"),
                "page_name": data.get("page_name", key),
                "page_access_token": data.get("page_access_token"),
            }
            for key, data in tokens.items()
        ]

        manager = TokenManager()
        expiring = await manager.get_all_expiring_tokens(token_list, days_threshold=14)

        if expiring:
            print(f"[{datetime.now()}] {len(expiring)} tokens expiring soon")
            notifier = TelegramNotifier()
            await notifier.send_token_expiry_alert(expiring)
        else:
            print(f"[{datetime.now()}] All tokens OK")

    except Exception as e:
        print(f"[{datetime.now()}] Token check error: {e}")
