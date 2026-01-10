"""Statistics API endpoints."""

import sys
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from fastapi import APIRouter, Query
from pydantic import BaseModel

# Add parent paths for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from database import db_connection, execute_query

router = APIRouter()


class DashboardStats(BaseModel):
    """Dashboard summary statistics."""
    total_posts: int = 0
    total_engagement: int = 0
    total_reactions: int = 0
    total_comments: int = 0
    total_shares: int = 0
    total_pages: int = 0
    avg_engagement_per_post: float = 0
    date_range: Dict[str, str] = {}


class DailyStats(BaseModel):
    """Daily engagement statistics."""
    date: str
    post_count: int = 0
    engagement: int = 0
    reactions: int = 0
    comments: int = 0
    shares: int = 0


class PostTypeStats(BaseModel):
    """Statistics by post type."""
    post_type: str
    count: int = 0
    total_engagement: int = 0
    avg_engagement: float = 0


@router.get("/dashboard", response_model=DashboardStats)
async def get_dashboard_stats(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
):
    """Get dashboard summary statistics."""
    with db_connection() as conn:
        where_clauses = []
        params = []

        if start_date:
            where_clauses.append("SUBSTR(publish_time, 1, 10) >= ?")
            params.append(start_date)
        if end_date:
            where_clauses.append("SUBSTR(publish_time, 1, 10) <= ?")
            params.append(end_date)

        where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

        cursor = execute_query(conn, f"""
            SELECT
                COUNT(*) as total_posts,
                COALESCE(SUM(total_engagement), 0) as total_engagement,
                COALESCE(SUM(reactions_total), 0) as total_reactions,
                COALESCE(SUM(comments_count), 0) as total_comments,
                COALESCE(SUM(shares_count), 0) as total_shares,
                MIN(SUBSTR(publish_time, 1, 10)) as min_date,
                MAX(SUBSTR(publish_time, 1, 10)) as max_date
            FROM posts
            WHERE {where_sql}
        """, tuple(params))

        row = cursor.fetchone()

        cursor2 = execute_query(conn, "SELECT COUNT(DISTINCT page_id) FROM pages")
        page_row = cursor2.fetchone()
        page_count = page_row[0] if page_row else 0

    total_posts = row[0] or 0 if row else 0
    total_engagement = row[1] or 0 if row else 0

    return DashboardStats(
        total_posts=total_posts,
        total_engagement=total_engagement,
        total_reactions=row[2] or 0 if row else 0,
        total_comments=row[3] or 0 if row else 0,
        total_shares=row[4] or 0 if row else 0,
        total_pages=page_count,
        avg_engagement_per_post=round(total_engagement / total_posts, 2) if total_posts > 0 else 0,
        date_range={"start": str(row[5] or "") if row else "", "end": str(row[6] or "") if row else ""},
    )


@router.get("/daily", response_model=List[DailyStats])
async def get_daily_stats(
    days: int = Query(30, ge=1, le=365),
    page_id: Optional[str] = None,
):
    """Get daily engagement statistics."""
    since_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

    page_filter = ""
    params = [since_date]
    if page_id:
        page_filter = "AND page_id = ?"
        params.append(page_id)

    with db_connection() as conn:
        cursor = execute_query(conn, f"""
            SELECT
                SUBSTR(publish_time, 1, 10) as date,
                COUNT(*) as post_count,
                COALESCE(SUM(total_engagement), 0) as engagement,
                COALESCE(SUM(reactions_total), 0) as reactions,
                COALESCE(SUM(comments_count), 0) as comments,
                COALESCE(SUM(shares_count), 0) as shares
            FROM posts
            WHERE SUBSTR(publish_time, 1, 10) >= ? {page_filter}
            GROUP BY SUBSTR(publish_time, 1, 10)
            ORDER BY date ASC
        """, tuple(params))

        rows = cursor.fetchall()

    return [
        DailyStats(
            date=str(row[0]),
            post_count=row[1],
            engagement=row[2],
            reactions=row[3],
            comments=row[4],
            shares=row[5],
        )
        for row in rows
    ]


@router.get("/time-series", response_model=List[DailyStats])
async def get_time_series(
    days: int = Query(30, ge=1, le=365),
    page_id: Optional[str] = None,
):
    """Get time series data for charts (alias for daily stats)."""
    return await get_daily_stats(days, page_id)


@router.get("/post-types", response_model=List[PostTypeStats])
async def get_post_type_stats(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
):
    """Get statistics grouped by post type."""
    where_clauses = []
    params = []

    if start_date:
        where_clauses.append("SUBSTR(publish_time, 1, 10) >= ?")
        params.append(start_date)
    if end_date:
        where_clauses.append("SUBSTR(publish_time, 1, 10) <= ?")
        params.append(end_date)

    where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

    with db_connection() as conn:
        cursor = execute_query(conn, f"""
            SELECT
                COALESCE(post_type, 'UNKNOWN') as post_type,
                COUNT(*) as count,
                COALESCE(SUM(total_engagement), 0) as total_engagement
            FROM posts
            WHERE {where_sql}
            GROUP BY post_type
            ORDER BY total_engagement DESC
        """, tuple(params))

        rows = cursor.fetchall()

    return [
        PostTypeStats(
            post_type=row[0],
            count=row[1],
            total_engagement=row[2],
            avg_engagement=round(row[2] / row[1], 2) if row[1] > 0 else 0,
        )
        for row in rows
    ]


@router.get("/page-comparison")
async def get_page_comparison(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Get page comparison statistics."""
    where_clauses = []
    params = []

    if start_date:
        where_clauses.append("SUBSTR(p.publish_time, 1, 10) >= ?")
        params.append(start_date)
    if end_date:
        where_clauses.append("SUBSTR(p.publish_time, 1, 10) <= ?")
        params.append(end_date)

    where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

    with db_connection() as conn:
        cursor = execute_query(conn, f"""
            SELECT
                pg.page_id,
                pg.page_name,
                pg.fan_count,
                COUNT(p.post_id) as post_count,
                COALESCE(SUM(p.total_engagement), 0) as total_engagement,
                COALESCE(SUM(p.reactions_total), 0) as reactions,
                COALESCE(SUM(p.comments_count), 0) as comments,
                COALESCE(SUM(p.shares_count), 0) as shares
            FROM pages pg
            LEFT JOIN posts p ON pg.page_id = p.page_id AND {where_sql}
            GROUP BY pg.page_id, pg.page_name, pg.fan_count
            ORDER BY total_engagement DESC
        """, tuple(params))

        rows = cursor.fetchall()

    return [
        {
            "page_id": row[0],
            "page_name": row[1],
            "fan_count": row[2] or 0,
            "post_count": row[3] or 0,
            "total_engagement": row[4] or 0,
            "reactions": row[5] or 0,
            "comments": row[6] or 0,
            "shares": row[7] or 0,
            "avg_engagement": round(row[4] / row[3], 2) if row[3] > 0 else 0,
        }
        for row in rows
    ]
