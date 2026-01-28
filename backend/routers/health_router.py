"""Health check and monitoring router"""
from fastapi import APIRouter, HTTPException, Request
from datetime import datetime, timezone
from typing import Optional
import logging

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.database import get_database, get_client
from core.db_monitor import get_query_stats, check_indexes, create_recommended_indexes, reset_stats
from core.security import require_auth, get_user_org_membership
from core.permissions import Permission, has_permission
from core.request_logger import get_request_metrics, reset_request_metrics

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/")
async def health_check():
    """Basic health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "2.0.0"
    }


@router.get("/db")
async def database_health():
    """
    Database health check with connection stats.
    Returns database connection status and basic metrics.
    """
    try:
        db = get_database()
        client = get_client()
        
        # Ping database
        await client.admin.command('ping')
        
        # Get server info
        server_info = await client.server_info()
        
        # Get database stats
        db_stats = await db.command("dbStats")
        
        return {
            "status": "healthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "connection": {
                "connected": True,
                "server_version": server_info.get("version", "unknown")
            },
            "database": {
                "name": db.name,
                "collections": db_stats.get("collections", 0),
                "objects": db_stats.get("objects", 0),
                "data_size_mb": round(db_stats.get("dataSize", 0) / (1024 * 1024), 2),
                "storage_size_mb": round(db_stats.get("storageSize", 0) / (1024 * 1024), 2),
                "indexes": db_stats.get("indexes", 0),
                "index_size_mb": round(db_stats.get("indexSize", 0) / (1024 * 1024), 2)
            }
        }
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return {
            "status": "unhealthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "error": str(e)
        }


@router.get("/db/stats")
async def query_statistics(request: Request):
    """
    Get query performance statistics.
    Requires authentication.
    """
    user = await require_auth(request)
    
    stats = get_query_stats()
    
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "stats": stats
    }


@router.post("/db/stats/reset")
async def reset_query_statistics(request: Request):
    """
    Reset query statistics.
    Requires authentication (admin only).
    """
    user = await require_auth(request)
    
    # Only allow admins - check if user is org admin in any org
    db = get_database()
    memberships = await db.org_memberships.find(
        {"user_id": user["user_id"], "role": {"$in": ["org_admin", "super_admin"]}},
        {"_id": 0}
    ).to_list(1)
    
    if not memberships:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    reset_stats()
    
    return {
        "status": "success",
        "message": "Query statistics reset",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.get("/db/indexes")
async def check_database_indexes(request: Request):
    """
    Check database indexes and get recommendations.
    Requires authentication.
    """
    user = await require_auth(request)
    
    db = get_database()
    index_info = await check_indexes(db)
    
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "indexes": index_info
    }


@router.post("/db/indexes/create")
async def create_indexes(request: Request):
    """
    Create all recommended indexes.
    Requires admin authentication.
    """
    user = await require_auth(request)
    
    # Only allow admins
    db = get_database()
    memberships = await db.org_memberships.find(
        {"user_id": user["user_id"], "role": {"$in": ["org_admin", "super_admin"]}},
        {"_id": 0}
    ).to_list(1)
    
    if not memberships:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    result = await create_recommended_indexes(db)
    
    return {
        "status": "success",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "result": result
    }


@router.get("/db/collections")
async def collection_stats(request: Request):
    """
    Get statistics for each collection.
    Requires authentication.
    """
    user = await require_auth(request)
    
    db = get_database()
    
    collections = ["users", "organizations", "org_memberships", "projects", "tasks", 
                   "comments", "time_entries", "notifications", "audit_logs", "automations"]
    
    stats = {}
    for coll_name in collections:
        try:
            count = await db[coll_name].count_documents({})
            stats[coll_name] = {"count": count}
        except Exception as e:
            stats[coll_name] = {"error": str(e)}
    
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "collections": stats
    }


@router.get("/db/slow-queries")
async def get_slow_queries(request: Request, limit: int = 50):
    """
    Get recent slow queries.
    Requires authentication.
    """
    user = await require_auth(request)
    
    from core.db_monitor import _recent_slow_queries, SLOW_QUERY_THRESHOLD, VERY_SLOW_QUERY_THRESHOLD
    
    # Get last N slow queries
    queries = _recent_slow_queries[-limit:] if _recent_slow_queries else []
    
    # Calculate statistics
    total_slow = len(_recent_slow_queries)
    very_slow_count = len([q for q in _recent_slow_queries if q.get("duration_ms", 0) >= VERY_SLOW_QUERY_THRESHOLD])
    
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "thresholds": {
            "slow_ms": SLOW_QUERY_THRESHOLD,
            "very_slow_ms": VERY_SLOW_QUERY_THRESHOLD
        },
        "summary": {
            "total_slow_queries": total_slow,
            "very_slow_queries": very_slow_count,
            "queries_returned": len(queries)
        },
        "queries": list(reversed(queries))  # Most recent first
    }


# =============================================
# Request Metrics Endpoints
# =============================================

@router.get("/metrics")
async def get_api_metrics(request: Request):
    """
    Get API request metrics and statistics.
    Requires authentication.
    
    Returns:
    - Total requests and errors
    - Error rate
    - Average response time
    - Status code distribution
    - Slowest endpoints
    - Endpoints with most errors
    - Recent slow requests
    - Recent errors
    """
    user = await require_auth(request)
    
    metrics = get_request_metrics()
    
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "metrics": metrics
    }


@router.post("/metrics/reset")
async def reset_api_metrics(request: Request):
    """
    Reset API request metrics.
    Requires admin authentication.
    """
    user = await require_auth(request)
    
    # Only allow admins
    db = get_database()
    memberships = await db.org_memberships.find(
        {"user_id": user["user_id"], "role": {"$in": ["org_admin", "super_admin"]}},
        {"_id": 0}
    ).to_list(1)
    
    if not memberships:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    reset_request_metrics()
    
    return {
        "status": "success",
        "message": "Request metrics reset",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.get("/metrics/summary")
async def get_metrics_summary():
    """
    Get a quick summary of API health metrics.
    Public endpoint (no auth required) for monitoring systems.
    """
    metrics = get_request_metrics()
    
    return {
        "status": "healthy" if metrics["error_rate_percent"] < 10 else "degraded",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_requests": metrics["total_requests"],
        "error_rate_percent": metrics["error_rate_percent"],
        "avg_response_time_ms": metrics["avg_response_time_ms"]
    }

