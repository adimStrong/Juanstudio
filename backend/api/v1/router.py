"""API v1 router - aggregates all endpoints."""

from fastapi import APIRouter

from .pages import router as pages_router
from .posts import router as posts_router
from .stats import router as stats_router
from .insights import router as insights_router
from .reports import router as reports_router

api_router = APIRouter()

api_router.include_router(pages_router, prefix="/pages", tags=["Pages"])
api_router.include_router(posts_router, prefix="/posts", tags=["Posts"])
api_router.include_router(stats_router, prefix="/stats", tags=["Statistics"])
api_router.include_router(insights_router, prefix="/insights", tags=["AI Insights"])
api_router.include_router(reports_router, prefix="/reports", tags=["Reports"])
