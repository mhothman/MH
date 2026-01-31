"""API Metrics Router - Performance monitoring and analytics"""
from fastapi import APIRouter, HTTPException, Request, Query
from typing import Optional
import logging

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.security import require_auth, require_permission
from core.permissions import Permission
from services.metrics_service import metrics_service

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/summary")
async def get_metrics_summary(
    request: Request,
    hours: int = Query(24, ge=1, le=168),  # Max 1 week
    org_id: Optional[str] = None
):
    """Get API metrics summary"""
    user = await require_auth(request)
    
    # Require admin permission for metrics
    if org_id:
        await require_permission(request, org_id, Permission.AUDIT_VIEW)
    
    summary = await metrics_service.get_metrics_summary(hours=hours, org_id=org_id)
    return summary


@router.get("/endpoints")
async def get_endpoint_stats(
    request: Request,
    hours: int = Query(24, ge=1, le=168),
    limit: int = Query(20, ge=1, le=100)
):
    """Get top endpoints by traffic"""
    user = await require_auth(request)
    
    stats = await metrics_service.get_endpoint_stats(hours=hours, limit=limit)
    return {"endpoints": stats, "period_hours": hours}


@router.get("/errors")
async def get_error_logs(
    request: Request,
    hours: int = Query(24, ge=1, le=168),
    limit: int = Query(50, ge=1, le=200)
):
    """Get recent API errors"""
    user = await require_auth(request)
    
    errors = await metrics_service.get_error_logs(hours=hours, limit=limit)
    return {"errors": errors, "total": len(errors)}


@router.get("/trends")
async def get_performance_trends(
    request: Request,
    hours: int = Query(24, ge=1, le=168),
    interval: int = Query(60, ge=15, le=360)  # Minutes
):
    """Get performance trends over time"""
    user = await require_auth(request)
    
    trends = await metrics_service.get_performance_trends(
        hours=hours,
        interval_minutes=interval
    )
    return {"trends": trends, "period_hours": hours}
