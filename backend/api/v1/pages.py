"""Pages API endpoints."""

import sys
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, Query
from pydantic import BaseModel

# Add parent paths for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from database import db_connection, execute_query

router = APIRouter()


class Page(BaseModel):
    """Page response model."""
    page_id: str
    page_name: str
    fan_count: Optional[int] = 0
    followers_count: Optional[int] = 0
    post_count: Optional[int] = 0
    total_engagement: Optional[int] = 0


@router.get("/", response_model=List[Page])
async def get_pages():
    """Get all pages with stats."""
    with db_connection() as conn:
        cursor = execute_query(conn, """
            SELECT
                p.page_id,
                p.page_name,
                p.fan_count,
                p.followers_count,
                COUNT(DISTINCT po.post_id) as post_count,
                COALESCE(SUM(po.total_engagement), 0) as total_engagement
            FROM pages p
            LEFT JOIN posts po ON p.page_id = po.page_id
            GROUP BY p.page_id, p.page_name, p.fan_count, p.followers_count
            ORDER BY total_engagement DESC
        """)

        rows = cursor.fetchall()

    return [
        Page(
            page_id=row[0],
            page_name=row[1],
            fan_count=row[2] or 0,
            followers_count=row[3] or 0,
            post_count=row[4] or 0,
            total_engagement=row[5] or 0,
        )
        for row in rows
    ]


@router.get("/{page_id}", response_model=Page)
async def get_page(page_id: str):
    """Get a single page by ID."""
    with db_connection() as conn:
        cursor = execute_query(conn, """
            SELECT
                p.page_id,
                p.page_name,
                p.fan_count,
                p.followers_count,
                COUNT(DISTINCT po.post_id) as post_count,
                COALESCE(SUM(po.total_engagement), 0) as total_engagement
            FROM pages p
            LEFT JOIN posts po ON p.page_id = po.page_id
            WHERE p.page_id = ?
            GROUP BY p.page_id, p.page_name, p.fan_count, p.followers_count
        """, (page_id,))

        row = cursor.fetchone()

    if not row:
        return Page(page_id=page_id, page_name="Not Found")

    return Page(
        page_id=row[0],
        page_name=row[1],
        fan_count=row[2] or 0,
        followers_count=row[3] or 0,
        post_count=row[4] or 0,
        total_engagement=row[5] or 0,
    )
