"""Database performance monitoring utilities"""
import time
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from functools import wraps
from collections import defaultdict
import asyncio

logger = logging.getLogger(__name__)

# Performance thresholds (in milliseconds)
SLOW_QUERY_THRESHOLD = 100  # Log queries taking longer than 100ms
VERY_SLOW_QUERY_THRESHOLD = 500  # Alert for queries taking longer than 500ms

# Query statistics storage (in-memory, resets on restart)
_query_stats: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
    "count": 0,
    "total_time_ms": 0,
    "avg_time_ms": 0,
    "max_time_ms": 0,
    "slow_count": 0,
    "last_execution": None
})

_recent_slow_queries: List[Dict[str, Any]] = []
MAX_SLOW_QUERY_HISTORY = 100


def record_query(operation: str, collection: str, duration_ms: float, query_filter: Optional[Dict] = None):
    """Record query execution statistics"""
    key = f"{collection}.{operation}"
    
    stats = _query_stats[key]
    stats["count"] += 1
    stats["total_time_ms"] += duration_ms
    stats["avg_time_ms"] = stats["total_time_ms"] / stats["count"]
    stats["max_time_ms"] = max(stats["max_time_ms"], duration_ms)
    stats["last_execution"] = datetime.now(timezone.utc).isoformat()
    
    # Track slow queries
    if duration_ms >= SLOW_QUERY_THRESHOLD:
        stats["slow_count"] += 1
        
        slow_query_record = {
            "operation": operation,
            "collection": collection,
            "duration_ms": round(duration_ms, 2),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "filter": str(query_filter)[:200] if query_filter else None  # Truncate for safety
        }
        
        _recent_slow_queries.append(slow_query_record)
        
        # Keep only recent slow queries
        if len(_recent_slow_queries) > MAX_SLOW_QUERY_HISTORY:
            _recent_slow_queries.pop(0)
        
        # Log slow queries
        if duration_ms >= VERY_SLOW_QUERY_THRESHOLD:
            logger.warning(f"VERY SLOW QUERY: {key} took {duration_ms:.2f}ms - Filter: {str(query_filter)[:100]}")
        else:
            logger.info(f"Slow query: {key} took {duration_ms:.2f}ms")


def get_query_stats() -> Dict[str, Any]:
    """Get aggregated query statistics"""
    total_queries = sum(s["count"] for s in _query_stats.values())
    total_slow = sum(s["slow_count"] for s in _query_stats.values())
    
    # Find slowest operations
    slowest = sorted(
        [(k, v) for k, v in _query_stats.items()],
        key=lambda x: x[1]["avg_time_ms"],
        reverse=True
    )[:10]
    
    return {
        "summary": {
            "total_queries": total_queries,
            "slow_queries": total_slow,
            "slow_query_percentage": round(total_slow / total_queries * 100, 2) if total_queries > 0 else 0,
            "collections_tracked": len(_query_stats)
        },
        "slowest_operations": [
            {
                "operation": k,
                "count": v["count"],
                "avg_ms": round(v["avg_time_ms"], 2),
                "max_ms": round(v["max_time_ms"], 2),
                "slow_count": v["slow_count"]
            }
            for k, v in slowest
        ],
        "recent_slow_queries": _recent_slow_queries[-20:]  # Last 20 slow queries
    }


def reset_stats():
    """Reset all query statistics"""
    global _query_stats, _recent_slow_queries
    _query_stats = defaultdict(lambda: {
        "count": 0,
        "total_time_ms": 0,
        "avg_time_ms": 0,
        "max_time_ms": 0,
        "slow_count": 0,
        "last_execution": None
    })
    _recent_slow_queries = []


class QueryTimer:
    """Context manager for timing database queries"""
    
    def __init__(self, operation: str, collection: str, query_filter: Optional[Dict] = None):
        self.operation = operation
        self.collection = collection
        self.query_filter = query_filter
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.perf_counter()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration_ms = (time.perf_counter() - self.start_time) * 1000
        record_query(self.operation, self.collection, duration_ms, self.query_filter)
        return False


# Index recommendations based on common query patterns
INDEX_RECOMMENDATIONS = {
    "tasks": [
        {"keys": [("project_id", 1), ("status", 1)], "name": "idx_tasks_project_status"},
        {"keys": [("assignee_ids", 1)], "name": "idx_tasks_assignees"},
        {"keys": [("due_date", 1), ("status", 1)], "name": "idx_tasks_due_date_status"},
        {"keys": [("org_id", 1), ("created_at", -1)], "name": "idx_tasks_org_created"},
        {"keys": [("task_id", 1)], "name": "idx_tasks_task_id"}
    ],
    "projects": [
        {"keys": [("org_id", 1), ("status", 1)], "name": "idx_projects_org_status"},
        {"keys": [("customer_id", 1)], "name": "idx_projects_customer"},
        {"keys": [("project_id", 1)], "name": "idx_projects_project_id"},
        {"keys": [("org_id", 1), ("created_at", -1)], "name": "idx_projects_org_created"}
    ],
    "audit_logs": [
        {"keys": [("org_id", 1), ("timestamp", -1)], "name": "idx_audit_org_timestamp"},
        {"keys": [("user_id", 1), ("timestamp", -1)], "name": "idx_audit_user_timestamp"},
        {"keys": [("resource_type", 1), ("resource_id", 1)], "name": "idx_audit_resource"}
    ],
    "org_memberships": [
        {"keys": [("user_id", 1), ("org_id", 1)], "name": "idx_membership_user_org"},
        {"keys": [("org_id", 1), ("role", 1)], "name": "idx_membership_org_role"}
    ],
    "time_entries": [
        {"keys": [("user_id", 1), ("start_time", -1)], "name": "idx_time_user_start"},
        {"keys": [("task_id", 1)], "name": "idx_time_task"}
    ],
    "users": [
        {"keys": [("user_id", 1)], "name": "idx_users_user_id"},
        {"keys": [("email", 1)], "name": "idx_users_email"}
    ],
    "organizations": [
        {"keys": [("org_id", 1)], "name": "idx_orgs_org_id"}
    ],
    "customers": [
        {"keys": [("customer_id", 1)], "name": "idx_customers_customer_id"},
        {"keys": [("org_id", 1)], "name": "idx_customers_org_id"}
    ],
    "comments": [
        {"keys": [("task_id", 1), ("created_at", -1)], "name": "idx_comments_task_created"}
    ],
    "notifications": [
        {"keys": [("user_id", 1), ("read", 1), ("created_at", -1)], "name": "idx_notifications_user_read_created"}
    ],
    "invitations": [
        {"keys": [("token", 1)], "name": "idx_invitations_token"},
        {"keys": [("org_id", 1), ("accepted", 1)], "name": "idx_invitations_org_accepted"}
    ],
    "automations": [
        {"keys": [("org_id", 1), ("enabled", 1)], "name": "idx_automations_org_enabled"}
    ],
    "attachments": [
        {"keys": [("task_id", 1)], "name": "idx_attachments_task_id"}
    ]
}


async def check_indexes(db) -> Dict[str, Any]:
    """Check existing indexes and provide recommendations"""
    results = {
        "existing_indexes": {},
        "recommendations": []
    }
    
    for collection_name in INDEX_RECOMMENDATIONS.keys():
        try:
            collection = db[collection_name]
            existing = await collection.index_information()
            results["existing_indexes"][collection_name] = list(existing.keys())
            
            # Check for missing recommended indexes
            for rec in INDEX_RECOMMENDATIONS[collection_name]:
                if rec["name"] not in existing:
                    results["recommendations"].append({
                        "collection": collection_name,
                        "index": rec["name"],
                        "keys": rec["keys"],
                        "reason": "Recommended for query performance"
                    })
        except Exception as e:
            logger.warning(f"Could not check indexes for {collection_name}: {e}")
    
    return results


async def create_recommended_indexes(db) -> Dict[str, Any]:
    """Create all recommended indexes"""
    created = []
    errors = []
    
    for collection_name, indexes in INDEX_RECOMMENDATIONS.items():
        collection = db[collection_name]
        for idx in indexes:
            try:
                await collection.create_index(idx["keys"], name=idx["name"], background=True)
                created.append(f"{collection_name}.{idx['name']}")
                logger.info(f"Created index: {collection_name}.{idx['name']}")
            except Exception as e:
                if "already exists" not in str(e).lower():
                    errors.append({"index": f"{collection_name}.{idx['name']}", "error": str(e)})
    
    return {"created": created, "errors": errors}
