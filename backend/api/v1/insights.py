"""AI Insights API endpoints."""

import sys
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

# Add parent paths for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from database import db_connection, execute_query

router = APIRouter()


class InsightResponse(BaseModel):
    """AI insight response."""
    insight: str
    generated_at: str
    source: str = "ai"  # "ai" or "fallback"


class ContentSuggestion(BaseModel):
    """Content suggestion from AI."""
    title: str
    type: str
    reasoning: str


@router.get("/daily", response_model=InsightResponse)
async def get_daily_insight(date: Optional[str] = None):
    """Get AI-generated daily insight."""
    if date is None:
        date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

    # Get stats for the date
    with db_connection() as conn:
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

        # Get top post
        cursor2 = execute_query(conn, """
            SELECT post_type, total_engagement
            FROM posts
            WHERE DATE(publish_time) = ?
            ORDER BY total_engagement DESC
            LIMIT 1
        """, (date,))
        top_post = cursor2.fetchone()

    stats = {
        "post_count": stats_row[0] or 0 if stats_row else 0,
        "total_engagement": stats_row[1] or 0 if stats_row else 0,
        "total_reactions": stats_row[2] or 0 if stats_row else 0,
        "total_comments": stats_row[3] or 0 if stats_row else 0,
        "total_shares": stats_row[4] or 0 if stats_row else 0,
    }

    # Try to use Ollama for AI insight
    try:
        from fb_analytics_core.ai import InsightsGenerator

        generator = InsightsGenerator()
        top_posts = [{"post_type": top_post[0], "total_engagement": top_post[1]}] if top_post else []

        insight = generator.generate_daily_insight_sync(stats, top_posts)

        return InsightResponse(
            insight=insight,
            generated_at=datetime.now().isoformat(),
            source="ai"
        )
    except Exception:
        # Fallback insight
        if stats["post_count"] == 0:
            insight = f"No posts on {date}. Consider maintaining a consistent posting schedule."
        else:
            avg = stats["total_engagement"] / stats["post_count"]
            top_type = top_post[0] if top_post else "content"
            insight = f"{top_type} content performing well with {avg:.0f} avg engagement per post."

        return InsightResponse(
            insight=insight,
            generated_at=datetime.now().isoformat(),
            source="fallback"
        )


@router.get("/suggestions", response_model=List[ContentSuggestion])
async def get_content_suggestions():
    """Get AI-generated content suggestions."""
    with db_connection() as conn:
        # Get post type performance
        cursor = execute_query(conn, """
            SELECT
                COALESCE(post_type, 'TEXT') as post_type,
                COUNT(*) as count,
                AVG(total_engagement) as avg_engagement
            FROM posts
            GROUP BY post_type
            ORDER BY avg_engagement DESC
        """)

        rows = cursor.fetchall()

    post_type_stats = {
        row[0]: {"count": row[1], "avg_engagement": row[2] or 0}
        for row in rows
    }

    # Try AI suggestions
    try:
        from fb_analytics_core.ai import InsightsGenerator

        generator = InsightsGenerator()
        # Get top posts for context
        with db_connection() as conn:
            cursor = execute_query(conn, """
                SELECT title, post_type, total_engagement
                FROM posts
                ORDER BY total_engagement DESC
                LIMIT 10
            """)
            top_posts = [
                {"title": row[0], "post_type": row[1], "total_engagement": row[2]}
                for row in cursor.fetchall()
            ]

        import asyncio
        suggestions = asyncio.run(
            generator.generate_content_suggestions(top_posts, post_type_stats)
        )

        return [
            ContentSuggestion(
                title=s.get("title", ""),
                type=s.get("type", ""),
                reasoning=s.get("reasoning", "")
            )
            for s in suggestions
        ]
    except Exception:
        # Fallback suggestions
        best_type = max(post_type_stats.items(), key=lambda x: x[1]["avg_engagement"], default=("VIDEO", {}))

        return [
            ContentSuggestion(
                title=f"Create more {best_type[0]} content",
                type=best_type[0],
                reasoning="This format shows highest average engagement"
            ),
            ContentSuggestion(
                title="Experiment with Reels",
                type="REEL",
                reasoning="Short-form video content typically has higher reach"
            ),
            ContentSuggestion(
                title="Interactive content with questions",
                type="TEXT",
                reasoning="Posts asking questions tend to generate more comments"
            ),
        ]


@router.get("/patterns")
async def get_engagement_patterns() -> Dict[str, Any]:
    """Get engagement pattern analysis."""
    since_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")

    with db_connection() as conn:
        cursor = execute_query(conn, """
            SELECT
                DATE(publish_time) as date,
                COALESCE(SUM(total_engagement), 0) as engagement
            FROM posts
            WHERE DATE(publish_time) >= ?
            GROUP BY DATE(publish_time)
            ORDER BY date ASC
        """, (since_date,))

        daily_data = [{"date": str(row[0]), "engagement": row[1]} for row in cursor.fetchall()]

    if not daily_data:
        return {"analysis": "Insufficient data for pattern analysis.", "trend": "unknown"}

    # Calculate trend
    total = sum(d["engagement"] for d in daily_data)
    avg = total / len(daily_data) if daily_data else 0

    recent = daily_data[-7:] if len(daily_data) >= 7 else daily_data
    recent_avg = sum(d["engagement"] for d in recent) / len(recent) if recent else 0

    if recent_avg > avg * 1.1:
        trend = "growing"
    elif recent_avg < avg * 0.9:
        trend = "declining"
    else:
        trend = "stable"

    return {
        "analysis": f"Engagement trend is {trend}. Average: {avg:.0f} per day.",
        "trend": trend,
        "average_engagement": round(avg, 2),
        "recent_average": round(recent_avg, 2),
        "daily_data": daily_data[-14:],  # Last 14 days
    }
