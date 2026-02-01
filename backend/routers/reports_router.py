"""Reports and dashboards router - Module 7"""
from fastapi import APIRouter, HTTPException, Request, Query
from fastapi.responses import StreamingResponse
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
import logging
import csv
import io
import json

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.database import get_database
from core.security import require_auth, get_user_org_membership, require_permission, check_permission
from core.permissions import Permission, has_permission
from models.enums import UserRole, TaskStatus, TaskPriority
from models.feature_flag import Features
from services.feature_service import feature_service
from services.audit_service import audit_service

logger = logging.getLogger(__name__)
router = APIRouter()

# ==================== PAGINATED DATA ROUTES ====================

@router.get("/org/{org_id}/projects")
async def get_paginated_projects(
    org_id: str,
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None),
    search: Optional[str] = Query(None)
):
    """
    Get paginated projects for an organization.
    
    Args:
        page: Page number (1-indexed)
        page_size: Number of items per page (max 100)
        status: Filter by project status
        search: Search in project name
    """
    db = get_database()
    user = await require_auth(request)
    
    membership = await get_user_org_membership(user["user_id"], org_id)
    if not membership:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Build query
    query = {"org_id": org_id}
    if status:
        query["status"] = status
    if search:
        query["name"] = {"$regex": search, "$options": "i"}
    
    # Get total count
    total = await db.projects.count_documents(query)
    
    # Calculate pagination
    skip = (page - 1) * page_size
    total_pages = (total + page_size - 1) // page_size
    
    # Get projects with pagination
    projects = await db.projects.find(query, {"_id": 0}).sort("created_at", -1).skip(skip).limit(page_size).to_list(page_size)
    
    # Enrich with task counts using aggregation
    if projects:
        project_ids = [p["project_id"] for p in projects]
        task_counts = await db.tasks.aggregate([
            {"$match": {"project_id": {"$in": project_ids}}},
            {"$group": {
                "_id": "$project_id",
                "total": {"$sum": 1},
                "completed": {"$sum": {"$cond": [{"$eq": ["$status", "done"]}, 1, 0]}}
            }}
        ]).to_list(100)
        
        task_counts_map = {tc["_id"]: tc for tc in task_counts}
        
        for project in projects:
            counts = task_counts_map.get(project["project_id"], {"total": 0, "completed": 0})
            project["task_count"] = counts["total"]
            project["completed_tasks"] = counts["completed"]
    
    return {
        "data": projects,
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1
        }
    }


@router.get("/org/{org_id}/tasks")
async def get_paginated_tasks(
    org_id: str,
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    project_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    assignee_id: Optional[str] = Query(None),
    overdue_only: bool = Query(False),
    search: Optional[str] = Query(None)
):
    """
    Get paginated tasks for an organization.
    
    Args:
        page: Page number (1-indexed)
        page_size: Number of items per page (max 100)
        project_id: Filter by project
        status: Filter by task status
        priority: Filter by priority
        assignee_id: Filter by assignee
        overdue_only: Show only overdue tasks
        search: Search in task title
    """
    db = get_database()
    user = await require_auth(request)
    
    membership = await get_user_org_membership(user["user_id"], org_id)
    if not membership:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Get project IDs for this org
    if project_id:
        project_ids = [project_id]
    else:
        projects = await db.projects.find({"org_id": org_id}, {"project_id": 1}).to_list(500)
        project_ids = [p["project_id"] for p in projects]
    
    # Build query
    query = {"project_id": {"$in": project_ids}}
    if status:
        query["status"] = status
    if priority:
        query["priority"] = priority
    if assignee_id:
        query["assignee_ids"] = assignee_id
    if search:
        query["title"] = {"$regex": search, "$options": "i"}
    if overdue_only:
        query["due_date"] = {"$lt": datetime.now(timezone.utc).isoformat()}
        query["status"] = {"$ne": "done"}
    
    # Get total count
    total = await db.tasks.count_documents(query)
    
    # Calculate pagination
    skip = (page - 1) * page_size
    total_pages = (total + page_size - 1) // page_size
    
    # Get tasks with pagination
    tasks = await db.tasks.find(query, {"_id": 0}).sort("created_at", -1).skip(skip).limit(page_size).to_list(page_size)
    
    return {
        "data": tasks,
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1
        }
    }


@router.get("/org/{org_id}/time-entries")
async def get_paginated_time_entries(
    org_id: str,
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user_id: Optional[str] = Query(None),
    task_id: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None)
):
    """
    Get paginated time entries for an organization.
    
    Args:
        page: Page number (1-indexed)
        page_size: Number of items per page (max 100)
        user_id: Filter by user
        task_id: Filter by task
        start_date: Filter entries from this date (ISO format)
        end_date: Filter entries until this date (ISO format)
    """
    db = get_database()
    user = await require_auth(request)
    
    membership = await get_user_org_membership(user["user_id"], org_id)
    if not membership:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Get project IDs for this org
    projects = await db.projects.find({"org_id": org_id}, {"project_id": 1}).to_list(500)
    project_ids = [p["project_id"] for p in projects]
    
    # Get task IDs for these projects
    tasks = await db.tasks.find({"project_id": {"$in": project_ids}}, {"task_id": 1}).to_list(2000)
    task_ids = [t["task_id"] for t in tasks]
    
    # Build query
    query = {"task_id": {"$in": task_ids}}
    if user_id:
        query["user_id"] = user_id
    if task_id:
        query["task_id"] = task_id
    if start_date:
        query["start_time"] = {"$gte": start_date}
    if end_date:
        if "start_time" in query:
            query["start_time"]["$lte"] = end_date
        else:
            query["start_time"] = {"$lte": end_date}
    
    # Get total count
    total = await db.time_entries.count_documents(query)
    
    # Calculate pagination
    skip = (page - 1) * page_size
    total_pages = (total + page_size - 1) // page_size
    
    # Get time entries with pagination
    entries = await db.time_entries.find(query, {"_id": 0}).sort("start_time", -1).skip(skip).limit(page_size).to_list(page_size)
    
    # Calculate total hours for this query
    total_minutes = 0
    for entry in entries:
        total_minutes += entry.get("duration_minutes", 0)
    
    return {
        "data": entries,
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1
        },
        "summary": {
            "total_entries_on_page": len(entries),
            "total_minutes_on_page": total_minutes,
            "total_hours_on_page": round(total_minutes / 60, 2)
        }
    }


# ==================== DASHBOARD ROUTES ====================
@router.get("/org/{org_id}/dashboard")
async def get_executive_dashboard(org_id: str, request: Request):
    db = get_database()
    user = await require_auth(request)

    membership = await get_user_org_membership(user["user_id"], org_id)
    _assert_report_permission(membership)

    projects = await fetch_projects(db, org_id)
    tasks = await fetch_tasks(db, projects)

    project_stats = calculate_project_stats(projects)
    task_stats = calculate_task_stats(tasks)

    workload = await calculate_member_workload(db, org_id, tasks)

    return {
        "projects": project_stats,
        "tasks": task_stats,
        "workload": workload,
    }
def _assert_report_permission(membership):
    if not membership:
        raise HTTPException(status_code=403, detail="Access denied")

    if not has_permission(membership["role"], Permission.REPORT_VIEW):
        raise HTTPException(
            status_code=403,
            detail="Permission denied: cannot view reports",
        )
async def fetch_projects(db, org_id: str):
    return await db.projects.find(
        {"org_id": org_id},
        {"_id": 0}
    ).to_list(500)


async def fetch_tasks(db, projects):
    project_ids = [p["project_id"] for p in projects]
    if not project_ids:
        return []

    return await db.tasks.find(
        {"project_id": {"$in": project_ids}},
        {"_id": 0}
    ).to_list(2000)
def calculate_project_stats(projects):
    stats = {
        "total": len(projects),
        "by_status": {},
    }

    for project in projects:
        status = project.get("status", "planned")
        stats["by_status"][status] = stats["by_status"].get(status, 0) + 1

    return stats
def calculate_task_stats(tasks):
    now = datetime.now(timezone.utc)

    stats = {
        "total": len(tasks),
        "completed": 0,
        "in_progress": 0,
        "overdue": 0,
        "by_priority": {},
        "by_status": {},
        "completion_rate": 0,
    }

    for task in tasks:
        status = task.get("status", "todo")
        priority = task.get("priority", "medium")

        stats["by_status"][status] = stats["by_status"].get(status, 0) + 1
        stats["by_priority"][priority] = stats["by_priority"].get(priority, 0) + 1

        if status == "done":
            stats["completed"] += 1
        elif status == "in_progress":
            stats["in_progress"] += 1

        if is_task_overdue(task, now):
            stats["overdue"] += 1

    if stats["total"] > 0:
        stats["completion_rate"] = round(
            stats["completed"] / stats["total"] * 100, 1
        )

    return stats
def is_task_overdue(task, now):
    if task.get("status") == "done":
        return False

    due_date = parse_due_date(task.get("due_date"))
    return bool(due_date and due_date < now)


def parse_due_date(due_str):
    if not isinstance(due_str, str):
        return None

    try:
        dt = datetime.fromisoformat(due_str.replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except Exception:
        return None
async def calculate_member_workload(db, org_id, tasks):
    members = await db.org_memberships.find(
        {"org_id": org_id},
        {"_id": 0}
    ).to_list(None)

    user_ids = [m["user_id"] for m in members]
    if not user_ids:
        return []

    users = await db.users.find(
        {"user_id": {"$in": user_ids}},
        {"_id": 0, "user_id": 1, "name": 1}
    ).to_list(None)

    users_map = {u["user_id"]: u for u in users}
    now = datetime.now(timezone.utc)

    workload = []

    for user_id in user_ids:
        user_tasks = [
            t for t in tasks if user_id in t.get("assignee_ids", [])
        ]

        user = users_map.get(user_id)
        if not user:
            continue

        workload.append({
            "user_id": user_id,
            "name": user.get("name", "Unknown"),
            "total_tasks": len(user_tasks),
            "completed": count_by_status(user_tasks, "done"),
            "in_progress": count_by_status(user_tasks, "in_progress"),
            "overdue": sum(
                1 for t in user_tasks if is_task_overdue(t, now)
            ),
        })

    return workload


def count_by_status(tasks, status):
    return sum(1 for t in tasks if t.get("status") == status)

    
    # Sort by total tasks
    workload.sort(key=lambda x: x["total_tasks"], reverse=True)
    
    return {
        "projects": project_stats,
        "tasks": task_stats,
        "workload": workload[:10],  # Top 10 members
        "generated_at": now.isoformat()
    }

@router.get("/org/{org_id}/productivity")
async def get_productivity_trends(
    org_id: str,
    request: Request,
    days: int = Query(30, le=365)
):
    """Get productivity trends over time"""
    db = get_database()
    user = await require_auth(request)
    
    membership = await get_user_org_membership(user["user_id"], org_id)
    if not membership:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Check REPORT_EXECUTIVE permission for advanced reports
    if not has_permission(membership["role"], Permission.REPORT_EXECUTIVE):
        raise HTTPException(status_code=403, detail="Permission denied: cannot view executive reports")
    
    # Check feature flag
    if not await feature_service.is_enabled(org_id, Features.ADVANCED_REPORTS):
        raise HTTPException(status_code=403, detail="Advanced reports not available on your plan")
    
    # Get projects for org
    projects = await db.projects.find({"org_id": org_id}, {"project_id": 1}).to_list(None)
    project_ids = [p["project_id"] for p in projects]
    
    # Calculate daily task completions
    start_date = datetime.now(timezone.utc) - timedelta(days=days)
    
    tasks = await db.tasks.find({
        "project_id": {"$in": project_ids},
        "updated_at": {"$gte": start_date.isoformat()}
    }, {"_id": 0}).to_list(None)
    
    # Group by day
    daily_stats = {}
    for i in range(days):
        date = (start_date + timedelta(days=i)).strftime("%Y-%m-%d")
        daily_stats[date] = {"created": 0, "completed": 0}
    
    for task in tasks:
        created_date = task.get("created_at", "")[:10]
        if created_date in daily_stats:
            daily_stats[created_date]["created"] += 1
        
        if task.get("status") == "done":
            updated_date = task.get("updated_at", "")[:10]
            if updated_date in daily_stats:
                daily_stats[updated_date]["completed"] += 1
    
    # Convert to list
    trends = [
        {"date": date, **stats}
        for date, stats in sorted(daily_stats.items())
    ]
    
    return {"trends": trends, "period_days": days}

@router.get("/org/{org_id}/resource-utilization")
async def get_resource_utilization(org_id: str, request: Request):
    """Get resource utilization metrics"""
    db = get_database()
    user = await require_auth(request)
    
    membership = await get_user_org_membership(user["user_id"], org_id)
    if not membership:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Get all members
    members = await db.org_memberships.find({"org_id": org_id}, {"_id": 0}).to_list(None)
    user_ids = [m["user_id"] for m in members]
    
    # Batch fetch all users at once (fix N+1)
    users_list = await db.users.find(
        {"user_id": {"$in": user_ids}}, 
        {"_id": 0, "user_id": 1, "name": 1}
    ).to_list(None)
    users_map = {u["user_id"]: u for u in users_list}
    
    # Get projects and tasks
    projects = await db.projects.find({"org_id": org_id}, {"_id": 0}).to_list(None)
    project_ids = [p["project_id"] for p in projects]
    
    tasks = await db.tasks.find({
        "project_id": {"$in": project_ids},
        "status": {"$ne": "done"}
    }, {"_id": 0}).to_list(None)
    
    # Get all task IDs for time entries batch query
    all_task_ids = [t["task_id"] for t in tasks]
    
    # Batch fetch all time entries at once (fix N+1)
    all_time_entries = await db.time_entries.find({
        "task_id": {"$in": all_task_ids}
    }, {"_id": 0, "user_id": 1, "task_id": 1, "duration_minutes": 1}).to_list(None)
    
    # Group time entries by user_id
    time_entries_by_user = {}
    for entry in all_time_entries:
        uid = entry.get("user_id")
        if uid not in time_entries_by_user:
            time_entries_by_user[uid] = []
        time_entries_by_user[uid].append(entry)
    
    # Calculate utilization per member
    utilization = []
    for user_id in user_ids:
        user_doc = users_map.get(user_id)
        user_tasks = [t for t in tasks if user_id in t.get("assignee_ids", [])]
        
        # Calculate estimated hours
        total_estimated = sum(t.get("estimated_hours", 0) or 0 for t in user_tasks)
        
        # Get time entries from pre-fetched data
        user_task_ids = {t["task_id"] for t in user_tasks}
        time_entries = [e for e in time_entries_by_user.get(user_id, []) if e.get("task_id") in user_task_ids]
        
        actual_hours = sum(e.get("duration_minutes", 0) for e in time_entries) / 60
        
        utilization.append({
            "user_id": user_id,
            "name": user_doc.get("name", "Unknown") if user_doc else "Unknown",
            "active_tasks": len(user_tasks),
            "estimated_hours": round(total_estimated, 1),
            "actual_hours": round(actual_hours, 1),
            "utilization_rate": round(actual_hours / max(total_estimated, 1) * 100, 1) if total_estimated > 0 else 0
        })
    
    utilization.sort(key=lambda x: x["active_tasks"], reverse=True)
    
    return {"utilization": utilization}

# ==================== EXPORT ROUTES ====================

@router.get("/org/{org_id}/export/projects")
async def export_projects(
    org_id: str,
    request: Request,
    format: str = Query("csv", regex="^(csv|json|xlsx)$")
):
    """Export projects data"""
    db = get_database()
    user = await require_auth(request)
    
    membership = await get_user_org_membership(user["user_id"], org_id)
    if not membership:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Check REPORT_EXPORT permission
    if not has_permission(membership["role"], Permission.REPORT_EXPORT):
        raise HTTPException(status_code=403, detail="Permission denied: cannot export reports")
    
    # Check feature flag
    if not await feature_service.is_enabled(org_id, Features.DATA_EXPORT):
        raise HTTPException(status_code=403, detail="Data export not available on your plan")
    
    projects = await db.projects.find({"org_id": org_id}, {"_id": 0}).to_list(None)
    
    await audit_service.log(user["user_id"], org_id, "export", "projects", org_id, {"format": format, "count": len(projects)})
    
    if format == "json":
        return {"projects": projects}
    
    # CSV export
    output = io.StringIO()
    if projects:
        writer = csv.DictWriter(output, fieldnames=["project_id", "name", "status", "start_date", "end_date", "created_at"])
        writer.writeheader()
        for p in projects:
            writer.writerow({
                "project_id": p.get("project_id"),
                "name": p.get("name"),
                "status": p.get("status"),
                "start_date": p.get("start_date"),
                "end_date": p.get("end_date"),
                "created_at": p.get("created_at")
            })
    
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode()),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=projects_{org_id}.csv"}
    )

@router.get("/org/{org_id}/export/tasks")
async def export_tasks(
    org_id: str,
    request: Request,
    project_id: Optional[str] = None,
    format: str = Query("csv", regex="^(csv|json)$")
):
    """Export tasks data"""
    db = get_database()
    user = await require_auth(request)
    
    membership = await get_user_org_membership(user["user_id"], org_id)
    if not membership:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Check REPORT_EXPORT permission
    if not has_permission(membership["role"], Permission.REPORT_EXPORT):
        raise HTTPException(status_code=403, detail="Permission denied: cannot export reports")
    
    # Check feature flag
    if not await feature_service.is_enabled(org_id, Features.DATA_EXPORT):
        raise HTTPException(status_code=403, detail="Data export not available on your plan")
    
    # Get project IDs
    if project_id:
        project_ids = [project_id]
    else:
        projects = await db.projects.find({"org_id": org_id}, {"project_id": 1}).to_list(None)
        project_ids = [p["project_id"] for p in projects]
    
    tasks = await db.tasks.find({"project_id": {"$in": project_ids}}, {"_id": 0}).to_list(None)
    
    await audit_service.log(user["user_id"], org_id, "export", "tasks", org_id, {"format": format, "count": len(tasks)})
    
    if format == "json":
        return {"tasks": tasks}
    
    # CSV export
    output = io.StringIO()
    if tasks:
        writer = csv.DictWriter(output, fieldnames=[
            "task_id", "project_id", "title", "status", "priority", 
            "due_date", "assignee_ids", "created_at"
        ])
        writer.writeheader()
        for t in tasks:
            writer.writerow({
                "task_id": t.get("task_id"),
                "project_id": t.get("project_id"),
                "title": t.get("title"),
                "status": t.get("status"),
                "priority": t.get("priority"),
                "due_date": t.get("due_date"),
                "assignee_ids": ",".join(t.get("assignee_ids", [])),
                "created_at": t.get("created_at")
            })
    
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode()),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=tasks_{org_id}.csv"}
    )

@router.get("/org/{org_id}/export/time-entries")
async def export_time_entries(
    org_id: str,
    request: Request,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    format: str = Query("csv", regex="^(csv|json)$")
):
    """Export time tracking data"""
    db = get_database()
    user = await require_auth(request)
    
    membership = await get_user_org_membership(user["user_id"], org_id)
    if not membership:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Check REPORT_EXPORT permission
    if not has_permission(membership["role"], Permission.REPORT_EXPORT):
        raise HTTPException(status_code=403, detail="Permission denied: cannot export reports")
    
    # Check feature flag
    if not await feature_service.is_enabled(org_id, Features.DATA_EXPORT):
        raise HTTPException(status_code=403, detail="Data export not available on your plan")
    
    # Get member user IDs
    members = await db.org_memberships.find({"org_id": org_id}, {"user_id": 1}).to_list(None)
    user_ids = [m["user_id"] for m in members]
    
    query = {"user_id": {"$in": user_ids}}
    if start_date:
        query["date"] = {"$gte": start_date}
    if end_date:
        if "date" in query:
            query["date"]["$lte"] = end_date
        else:
            query["date"] = {"$lte": end_date}
    
    entries = await db.time_entries.find(query, {"_id": 0}).to_list(None)
    
    await audit_service.log(user["user_id"], org_id, "export", "time_entries", org_id, {"format": format, "count": len(entries)})
    
    if format == "json":
        return {"time_entries": entries}
    
    # CSV export
    output = io.StringIO()
    if entries:
        writer = csv.DictWriter(output, fieldnames=[
            "entry_id", "task_id", "user_id", "duration_minutes", 
            "description", "date", "created_at"
        ])
        writer.writeheader()
        writer.writerows(entries)
    
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode()),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=time_entries_{org_id}.csv"}
    )


# ==================== TIMELINE ROUTE ====================

@router.get("/timeline")
async def get_timeline_data(
    request: Request,
    project_id: str = Query(..., description="Project ID to get timeline for")
):
    """
    Get timeline/Gantt chart data for a project.
    
    Returns tasks with their dates for Gantt chart visualization.
    """
    db = get_database()
    user = await require_auth(request)
    
    # Get project and check access
    project = await db.projects.find_one({"project_id": project_id}, {"_id": 0})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    membership = await get_user_org_membership(user["user_id"], project["org_id"])
    if not membership:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Get all tasks for the project
    tasks = await db.tasks.find(
        {"project_id": project_id},
        {"_id": 0}
    ).to_list(None)
    
    # Get all users for assignee names
    user_ids = set()
    for task in tasks:
        user_ids.update(task.get("assignee_ids", []))
    
    users = {}
    if user_ids:
        user_docs = await db.users.find(
            {"user_id": {"$in": list(user_ids)}},
            {"_id": 0, "user_id": 1, "name": 1}
        ).to_list(None)
        users = {u["user_id"]: u["name"] for u in user_docs}
    
    # Process tasks for timeline
    timeline_tasks = []
    for task in tasks:
        # Get assignee names
        assignees = [users.get(uid, "Unknown") for uid in task.get("assignee_ids", [])]
        
        timeline_tasks.append({
            "task_id": task["task_id"],
            "title": task["title"],
            "description": task.get("description", ""),
            "status": task.get("status", "todo"),
            "priority": task.get("priority", "medium"),
            "start_date": task.get("start_date"),
            "due_date": task.get("due_date"),
            "estimated_hours": task.get("estimated_hours", 0),
            "actual_hours": task.get("actual_hours", 0),
            "blocked_by": task.get("blocked_by", []),
            "blocks": task.get("blocks", []),
            "assignee_ids": task.get("assignee_ids", []),
            "assignees": assignees,
            "progress": 100 if task.get("status") == "done" else (50 if task.get("status") == "in_progress" else 0),
        })
    
    return {
        "project": {
            "project_id": project["project_id"],
            "name": project["name"],
            "start_date": project.get("start_date"),
            "target_date": project.get("target_date"),
        },
        "tasks": timeline_tasks,
        "generated_at": datetime.now(timezone.utc).isoformat()
    }

