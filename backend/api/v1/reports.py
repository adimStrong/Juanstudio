"""Reports API endpoints."""

import sys
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from fastapi import APIRouter
from pydantic import BaseModel

# Add parent paths for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from database import db_connection, execute_query, DATABASE_PATH

router = APIRouter()


class ReportRequest(BaseModel):
    """Report generation request."""
    date: Optional[str] = None
    include_ai_insight: bool = True


class DailyReportResponse(BaseModel):
    """Daily report response."""
    date: str
    stats: Dict[str, Any]
    latest_post: Optional[Dict[str, Any]] = None
    top_posts: list = []
    ai_insight: Optional[str] = None
    telegram_message: Optional[str] = None


@router.get("/daily", response_model=DailyReportResponse)
async def get_daily_report(
    date: Optional[str] = None,
    include_ai: bool = True,
):
    """Generate daily report data."""
    try:
        from fb_analytics_core.reports import DailyReportGenerator
        from fb_analytics_core.ai import InsightsGenerator

        generator = DailyReportGenerator(DATABASE_PATH)
        report_data = generator.generate_report_data(date)

        ai_insight = None
        if include_ai:
            try:
                insights = InsightsGenerator()
                ai_insight = insights.generate_daily_insight_sync(
                    report_data["stats"],
                    report_data.get("top_posts", [])
                )
            except Exception:
                pass

        telegram_message = generator.format_telegram_message(report_data, ai_insight)

        return DailyReportResponse(
            date=report_data["date"],
            stats=report_data["stats"],
            latest_post=report_data.get("latest_post"),
            top_posts=report_data.get("top_posts", []),
            ai_insight=ai_insight,
            telegram_message=telegram_message,
        )
    except ImportError:
        # Fallback without shared library
        if date is None:
            date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

        with db_connection() as conn:
            # Get stats
            cursor = execute_query(conn, """
                SELECT
                    COUNT(*) as post_count,
                    COALESCE(SUM(total_engagement), 0) as total_engagement,
                    COALESCE(SUM(reactions_total), 0) as reactions,
                    COALESCE(SUM(comments_count), 0) as comments,
                    COALESCE(SUM(shares_count), 0) as shares
                FROM posts
                WHERE DATE(publish_time) = ?
            """, (date,))
            stats_row = cursor.fetchone()

            stats = {
                "date": date,
                "post_count": stats_row[0] or 0 if stats_row else 0,
                "total_engagement": stats_row[1] or 0 if stats_row else 0,
                "total_reactions": stats_row[2] or 0 if stats_row else 0,
                "total_comments": stats_row[3] or 0 if stats_row else 0,
                "total_shares": stats_row[4] or 0 if stats_row else 0,
            }

            # Get latest post
            cursor2 = execute_query(conn, """
                SELECT
                    p.post_id, p.title, p.post_type, p.total_engagement, pg.page_name
                FROM posts p
                LEFT JOIN pages pg ON p.page_id = pg.page_id
                ORDER BY p.publish_time DESC
                LIMIT 1
            """)
            latest_row = cursor2.fetchone()

            latest_post = None
            if latest_row:
                latest_post = {
                    "post_id": latest_row[0],
                    "title": latest_row[1],
                    "post_type": latest_row[2],
                    "total_engagement": latest_row[3],
                    "page_name": latest_row[4],
                }

            # Get top posts
            cursor3 = execute_query(conn, """
                SELECT
                    p.title, p.post_type, p.total_engagement, pg.page_name
                FROM posts p
                LEFT JOIN pages pg ON p.page_id = pg.page_id
                WHERE DATE(p.publish_time) = ?
                ORDER BY p.total_engagement DESC
                LIMIT 5
            """, (date,))
            top_posts = [
                {
                    "title": row[0],
                    "post_type": row[1],
                    "total_engagement": row[2],
                    "page_name": row[3],
                }
                for row in cursor3.fetchall()
            ]

        return DailyReportResponse(
            date=date,
            stats=stats,
            latest_post=latest_post,
            top_posts=top_posts,
            ai_insight=None,
            telegram_message=None,
        )


@router.post("/send-telegram")
async def send_telegram_report(date: Optional[str] = None) -> Dict[str, Any]:
    """Send daily report to Telegram."""
    try:
        from fb_analytics_core.reports import DailyReportGenerator
        from fb_analytics_core.ai import InsightsGenerator
        from fb_analytics_core.notifications import TelegramNotifier

        generator = DailyReportGenerator(DATABASE_PATH)
        report_data = generator.generate_report_data(date)

        # Generate AI insight
        try:
            insights = InsightsGenerator()
            ai_insight = insights.generate_daily_insight_sync(
                report_data["stats"],
                report_data.get("top_posts", [])
            )
        except Exception:
            ai_insight = None

        # Format and send
        message = generator.format_telegram_message(report_data, ai_insight)

        notifier = TelegramNotifier()
        result = notifier.send_sync(message)

        return {
            "success": result.get("ok", False),
            "date": report_data["date"],
            "message_length": len(message),
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }
