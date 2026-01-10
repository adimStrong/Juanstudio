"""Posts API endpoints."""

import sys
from pathlib import Path
from typing import List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Query
from pydantic import BaseModel

# Add parent paths for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from database import db_connection, execute_query

router = APIRouter()


class Post(BaseModel):
    """Post response model."""
    post_id: str
    page_id: str
    page_name: Optional[str] = None
    title: Optional[str] = None
    post_type: Optional[str] = None
    publish_time: Optional[str] = None
    reactions_total: int = 0
    comments_count: int = 0
    shares_count: int = 0
    total_engagement: int = 0
    permalink: Optional[str] = None


class PostsResponse(BaseModel):
    """Paginated posts response."""
    posts: List[Post]
    total: int
    page: int
    per_page: int


@router.get("/", response_model=PostsResponse)
async def get_posts(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    page_id: Optional[str] = None,
    post_type: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    search: Optional[str] = None,
):
    """Get posts with filtering and pagination."""
    # Build query
    where_clauses = []
    params = []

    if page_id:
        where_clauses.append("p.page_id = ?")
        params.append(page_id)

    if post_type:
        where_clauses.append("p.post_type = ?")
        params.append(post_type)

    if start_date:
        where_clauses.append("DATE(p.publish_time) >= ?")
        params.append(start_date)

    if end_date:
        where_clauses.append("DATE(p.publish_time) <= ?")
        params.append(end_date)

    if search:
        where_clauses.append("p.title LIKE ?")
        params.append(f"%{search}%")

    where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

    with db_connection() as conn:
        # Count total
        cursor = execute_query(conn, f"""
            SELECT COUNT(*)
            FROM posts p
            WHERE {where_sql}
        """, tuple(params))
        total = cursor.fetchone()[0]

        # Get posts
        offset = (page - 1) * per_page
        cursor = execute_query(conn, f"""
            SELECT
                p.post_id,
                p.page_id,
                pg.page_name,
                p.title,
                p.post_type,
                p.publish_time,
                p.reactions_total,
                p.comments_count,
                p.shares_count,
                p.total_engagement,
                p.permalink
            FROM posts p
            LEFT JOIN pages pg ON p.page_id = pg.page_id
            WHERE {where_sql}
            ORDER BY p.publish_time DESC
            LIMIT ? OFFSET ?
        """, tuple(params + [per_page, offset]))

        rows = cursor.fetchall()

    posts = [
        Post(
            post_id=row[0],
            page_id=row[1],
            page_name=row[2],
            title=row[3],
            post_type=row[4],
            publish_time=str(row[5]) if row[5] else None,
            reactions_total=row[6] or 0,
            comments_count=row[7] or 0,
            shares_count=row[8] or 0,
            total_engagement=row[9] or 0,
            permalink=row[10],
        )
        for row in rows
    ]

    return PostsResponse(
        posts=posts,
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get("/latest", response_model=Post)
async def get_latest_post():
    """Get the most recent post."""
    with db_connection() as conn:
        cursor = execute_query(conn, """
            SELECT
                p.post_id,
                p.page_id,
                pg.page_name,
                p.title,
                p.post_type,
                p.publish_time,
                p.reactions_total,
                p.comments_count,
                p.shares_count,
                p.total_engagement,
                p.permalink
            FROM posts p
            LEFT JOIN pages pg ON p.page_id = pg.page_id
            ORDER BY p.publish_time DESC
            LIMIT 1
        """)

        row = cursor.fetchone()

    if not row:
        return Post(post_id="", page_id="")

    return Post(
        post_id=row[0],
        page_id=row[1],
        page_name=row[2],
        title=row[3],
        post_type=row[4],
        publish_time=str(row[5]) if row[5] else None,
        reactions_total=row[6] or 0,
        comments_count=row[7] or 0,
        shares_count=row[8] or 0,
        total_engagement=row[9] or 0,
        permalink=row[10],
    )


@router.get("/top", response_model=List[Post])
async def get_top_posts(
    limit: int = Query(10, ge=1, le=100),
    days: int = Query(7, ge=1, le=90),
):
    """Get top performing posts."""
    since_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

    with db_connection() as conn:
        cursor = execute_query(conn, """
            SELECT
                p.post_id,
                p.page_id,
                pg.page_name,
                p.title,
                p.post_type,
                p.publish_time,
                p.reactions_total,
                p.comments_count,
                p.shares_count,
                p.total_engagement,
                p.permalink
            FROM posts p
            LEFT JOIN pages pg ON p.page_id = pg.page_id
            WHERE DATE(p.publish_time) >= ?
            ORDER BY p.total_engagement DESC
            LIMIT ?
        """, (since_date, limit))

        rows = cursor.fetchall()

    return [
        Post(
            post_id=row[0],
            page_id=row[1],
            page_name=row[2],
            title=row[3],
            post_type=row[4],
            publish_time=str(row[5]) if row[5] else None,
            reactions_total=row[6] or 0,
            comments_count=row[7] or 0,
            shares_count=row[8] or 0,
            total_engagement=row[9] or 0,
            permalink=row[10],
        )
        for row in rows
    ]
