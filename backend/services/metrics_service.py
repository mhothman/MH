"""API Metrics Service - Track and analyze API performance"""
import logging
import io
import csv
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from collections import defaultdict

from fastapi.responses import StreamingResponse
from core.database import get_database

logger = logging.getLogger(__name__)


class MetricsService:
    """Service for API metrics collection and analysis"""
    
    async def record_request(
        self,
        method: str,
        endpoint: str,
        status_code: int,
        response_time_ms: float,
        user_id: Optional[str] = None,
        org_id: Optional[str] = None,
        error_message: Optional[str] = None
    ) -> None:
        """Record an API request metric"""
        db = get_database()
        
        metric = {
            "metric_id": f"metric_{datetime.now().timestamp()}_{hash(endpoint)}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "method": method,
            "endpoint": endpoint,
            "status_code": status_code,
            "response_time_ms": response_time_ms,
            "user_id": user_id,
            "org_id": org_id,
            "error_message": error_message,
            "is_error": status_code >= 400,
            "is_slow": response_time_ms > 1000  # > 1 second
        }
        
        try:
            await db.api_metrics.insert_one(metric)
        except Exception as e:
            logger.error(f"Failed to record metric: {e}")
    
    async def get_metrics_summary(
        self,
        hours: int = 24,
        org_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get metrics summary for the last N hours"""
        db = get_database()
        
        cutoff_time = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
        
        query = {"timestamp": {"$gte": cutoff_time}}
        if org_id:
            query["org_id"] = org_id
        
        # Aggregate metrics
        pipeline = [
            {"$match": query},
            {"$group": {
                "_id": None,
                "total_requests": {"$sum": 1},
                "error_count": {"$sum": {"$cond": ["$is_error", 1, 0]}},
                "slow_requests": {"$sum": {"$cond": ["$is_slow", 1, 0]}},
                "avg_response_time": {"$avg": "$response_time_ms"},
                "max_response_time": {"$max": "$response_time_ms"},
                "min_response_time": {"$min": "$response_time_ms"}
            }}
        ]
        
        result = await db.api_metrics.aggregate(pipeline).to_list(1)
        
        if not result:
            return {
                "total_requests": 0,
                "error_count": 0,
                "slow_requests": 0,
                "avg_response_time": 0,
                "max_response_time": 0,
                "min_response_time": 0,
                "error_rate": 0,
                "period_hours": hours
            }
        
        stats = result[0]
        return {
            "total_requests": stats["total_requests"],
            "error_count": stats["error_count"],
            "slow_requests": stats["slow_requests"],
            "avg_response_time": round(stats["avg_response_time"], 2),
            "max_response_time": round(stats["max_response_time"], 2),
            "min_response_time": round(stats["min_response_time"], 2),
            "error_rate": round((stats["error_count"] / stats["total_requests"]) * 100, 2) if stats["total_requests"] > 0 else 0,
            "period_hours": hours
        }
    
    async def get_endpoint_stats(
        self,
        hours: int = 24,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Get top endpoints by request count"""
        db = get_database()
        
        cutoff_time = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
        
        pipeline = [
            {"$match": {"timestamp": {"$gte": cutoff_time}}},
            {"$group": {
                "_id": "$endpoint",
                "count": {"$sum": 1},
                "avg_response_time": {"$avg": "$response_time_ms"},
                "error_count": {"$sum": {"$cond": ["$is_error", 1, 0]}}
            }},
            {"$sort": {"count": -1}},
            {"$limit": limit}
        ]
        
        results = await db.api_metrics.aggregate(pipeline).to_list(limit)
        
        return [
            {
                "endpoint": r["_id"],
                "request_count": r["count"],
                "avg_response_time": round(r["avg_response_time"], 2),
                "error_count": r["error_count"],
                "error_rate": round((r["error_count"] / r["count"]) * 100, 2) if r["count"] > 0 else 0
            }
            for r in results
        ]
    
    async def get_error_logs(
        self,
        hours: int = 24,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get recent error logs"""
        db = get_database()
        
        cutoff_time = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
        
        errors = await db.api_metrics.find(
            {
                "timestamp": {"$gte": cutoff_time},
                "is_error": True
            },
            {"_id": 0}
        ).sort("timestamp", -1).limit(limit).to_list(limit)
        
        return errors
    
    async def get_performance_trends(
        self,
        hours: int = 24,
        interval_minutes: int = 60
    ) -> List[Dict[str, Any]]:
        """Get performance trends over time"""
        db = get_database()
        
        cutoff_time = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
        
        # Group by time intervals
        pipeline = [
            {"$match": {"timestamp": {"$gte": cutoff_time}}},
            {"$project": {
                "timestamp": 1,
                "response_time_ms": 1,
                "is_error": 1,
                "interval": {
                    "$dateToString": {
                        "format": "%Y-%m-%d %H:00",
                        "date": {"$toDate": "$timestamp"}
                    }
                }
            }},
            {"$group": {
                "_id": "$interval",
                "avg_response_time": {"$avg": "$response_time_ms"},
                "request_count": {"$sum": 1},
                "error_count": {"$sum": {"$cond": ["$is_error", 1, 0]}}
            }},
            {"$sort": {"_id": 1}}
        ]
        
        results = await db.api_metrics.aggregate(pipeline).to_list(100)
        
        return [
            {
                "time_period": r["_id"],
                "avg_response_time": round(r["avg_response_time"], 2),
                "request_count": r["request_count"],
                "error_count": r["error_count"],
                "error_rate": round((r["error_count"] / r["request_count"]) * 100, 2) if r["request_count"] > 0 else 0
            }
            for r in results
        ]


# Singleton instance
metrics_service = MetricsService()
