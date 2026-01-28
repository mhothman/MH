"""Dashboard router - main app dashboard"""
from fastapi import APIRouter, HTTPException, Request
from datetime import datetime, timezone, timedelta
from typing import Optional
import logging

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.database import get_database
from core.security import require_auth, get_user_org_membership

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/")
async def get_dashboard(request: Request, org_id: Optional[str] = None):
    """
    Get main dashboard data for the current user.
    
    Returns overview stats, recent activity, and upcoming tasks.
    """
    db = get_database()
    user = await require_auth(request)
    
    # Get user's organizations
    if org_id:
        membership = await get_user_org_membership(user["user_id"], org_id)
        if not membership:
            raise HTTPException(status_code=403, detail="Access denied")
        org_ids = [org_id]
    else:
        memberships = await db.org_memberships.find(
            {"user_id": user["user_id"]},
            {"_id": 0}
        ).to_list(100)
        org_ids = [m["org_id"] for m in memberships]
    
    if not org_ids:
        return {
            "projects": {"total": 0, "active": 0},
            "tasks": {"total": 0, "completed": 0, "overdue": 0, "assigned_to_me": 0},
            "recent_tasks": [],
            "upcoming_deadlines": [],
            "recent_activity": []
        }
    
    now = datetime.now(timezone.utc)
    
    # Get projects (limit to 500 for performance)
    projects = await db.projects.find(
        {"org_id": {"$in": org_ids}},
        {"_id": 0}
    ).to_list(500)
    
    project_ids = [p["project_id"] for p in projects]
    active_projects = len([p for p in projects if p.get("status") == "active"])
    
    # Get tasks (limit to 2000 for performance)
    tasks = await db.tasks.find(
        {"project_id": {"$in": project_ids}},
        {"_id": 0}
    ).to_list(2000)
    
    total_tasks = len(tasks)
    completed_tasks = len([t for t in tasks if t.get("status") == "done"])
    
    # Tasks assigned to current user
    my_tasks = [t for t in tasks if user["user_id"] in t.get("assignee_ids", [])]
    
    # Overdue tasks
    overdue_tasks = []
    for t in tasks:
        if t.get("due_date") and t.get("status") != "done":
            try:
                due = t["due_date"]
                if isinstance(due, str):
                    due = datetime.fromisoformat(due.replace("Z", "+00:00"))
                if due < now:
                    overdue_tasks.append(t)
            except Exception:
                pass
    
    # Upcoming deadlines (next 7 days)
    upcoming = []
    week_later = now + timedelta(days=7)
    for t in tasks:
        if t.get("due_date") and t.get("status") != "done":
            try:
                due = t["due_date"]
                if isinstance(due, str):
                    due = datetime.fromisoformat(due.replace("Z", "+00:00"))
                if now <= due <= week_later:
                    t["due_date_parsed"] = due
                    upcoming.append(t)
            except Exception:
                pass
    
    upcoming.sort(key=lambda x: x.get("due_date_parsed", now))
    
    # Format upcoming tasks
    upcoming_formatted = []
    for t in upcoming[:10]:
        project = next((p for p in projects if p["project_id"] == t["project_id"]), None)
        upcoming_formatted.append({
            "task_id": t["task_id"],
            "title": t["title"],
            "due_date": t.get("due_date"),
            "priority": t.get("priority"),
            "status": t.get("status"),
            "project_id": t["project_id"],
            "project_name": project["name"] if project else "Unknown"
        })
    
    # Recent tasks (last modified)
    recent_tasks = sorted(tasks, key=lambda x: x.get("updated_at", ""), reverse=True)[:10]
    recent_formatted = []
    for t in recent_tasks:
        project = next((p for p in projects if p["project_id"] == t["project_id"]), None)
        recent_formatted.append({
            "task_id": t["task_id"],
            "title": t["title"],
            "status": t.get("status"),
            "priority": t.get("priority"),
            "updated_at": t.get("updated_at"),
            "project_id": t["project_id"],
            "project_name": project["name"] if project else "Unknown"
        })
    
    # Recent activity (from audit logs)
    recent_activity = await db.audit_logs.find(
        {"org_id": {"$in": org_ids}},
        {"_id": 0}
    ).sort("timestamp", -1).limit(20).to_list(20)
    
    # Batch fetch user names to avoid N+1 queries
    user_ids = list(set([a["user_id"] for a in recent_activity if a.get("user_id") and a["user_id"] != "system"]))
    user_map = {}
    if user_ids:
        users = await db.users.find({"user_id": {"$in": user_ids}}, {"_id": 0, "user_id": 1, "name": 1}).to_list(100)
        user_map = {u["user_id"]: u.get("name", "Unknown") for u in users}
    
    # Add user names to activity
    for activity in recent_activity:
        if activity.get("user_id") and activity["user_id"] != "system":
            activity["user_name"] = user_map.get(activity["user_id"], "Unknown")
        else:
            activity["user_name"] = "System"
    
    return {
        "projects": {
            "total": len(projects),
            "active": active_projects,
            "by_status": _count_by_field(projects, "status")
        },
        "tasks": {
            "total": total_tasks,
            "completed": completed_tasks,
            "completion_rate": round(completed_tasks / max(total_tasks, 1) * 100, 1),
            "overdue": len(overdue_tasks),
            "assigned_to_me": len(my_tasks),
            "my_completed": len([t for t in my_tasks if t.get("status") == "done"]),
            "by_status": _count_by_field(tasks, "status"),
            "by_priority": _count_by_field(tasks, "priority")
        },
        "recent_tasks": recent_formatted,
        "upcoming_deadlines": upcoming_formatted,
        "recent_activity": recent_activity,
        "generated_at": now.isoformat()
    }

def _count_by_field(items: list, field: str) -> dict:
    """Helper to count items by a field value"""
    counts = {}
    for item in items:
        value = item.get(field, "unknown")
        counts[value] = counts.get(value, 0) + 1
    return counts

@router.get("/my-tasks")
async def get_my_tasks(request: Request, status: Optional[str] = None):
    """Get tasks assigned to current user"""
    db = get_database()
    user = await require_auth(request)
    
    # Get user's organizations
    memberships = await db.org_memberships.find(
        {"user_id": user["user_id"]},
        {"_id": 0, "org_id": 1}
    ).to_list(100)
    org_ids = [m["org_id"] for m in memberships]
    
    # Get projects
    projects = await db.projects.find(
        {"org_id": {"$in": org_ids}},
        {"project_id": 1, "name": 1}
    ).to_list(None)
    project_ids = [p["project_id"] for p in projects]
    project_map = {p["project_id"]: p["name"] for p in projects}
    
    # Get tasks
    query = {
        "project_id": {"$in": project_ids},
        "assignee_ids": user["user_id"]
    }
    if status:
        query["status"] = status
    
    tasks = await db.tasks.find(query, {"_id": 0}).sort("due_date", 1).to_list(100)
    
    for t in tasks:
        t["project_name"] = project_map.get(t["project_id"], "Unknown")
        t["created_at"] = datetime.fromisoformat(t["created_at"]) if isinstance(t.get("created_at"), str) else t.get("created_at")
        t["updated_at"] = datetime.fromisoformat(t.get("updated_at", t.get("created_at", ""))) if isinstance(t.get("updated_at"), str) else t.get("updated_at")
    
    return tasks

@router.get("/stats")
async def get_quick_stats(request: Request, org_id: Optional[str] = None):
    """Get quick stats for header/sidebar display"""
    db = get_database()
    user = await require_auth(request)
    
    # Get user's organizations
    if org_id:
        membership = await get_user_org_membership(user["user_id"], org_id)
        if not membership:
            raise HTTPException(status_code=403, detail="Access denied")
        org_ids = [org_id]
    else:
        memberships = await db.org_memberships.find(
            {"user_id": user["user_id"]},
            {"_id": 0, "org_id": 1}
        ).to_list(100)
        org_ids = [m["org_id"] for m in memberships]
    
    # Get projects
    projects = await db.projects.find(
        {"org_id": {"$in": org_ids}},
        {"project_id": 1}
    ).to_list(None)
    project_ids = [p["project_id"] for p in projects]
    
    # Count tasks
    total_tasks = await db.tasks.count_documents({"project_id": {"$in": project_ids}})
    my_tasks = await db.tasks.count_documents({
        "project_id": {"$in": project_ids},
        "assignee_ids": user["user_id"],
        "status": {"$ne": "done"}
    })
    
    # Unread notifications
    unread_notifications = await db.notifications.count_documents({
        "user_id": user["user_id"],
        "read": False
    })
    
    return {
        "projects": len(projects),
        "tasks": total_tasks,
        "my_pending_tasks": my_tasks,
        "unread_notifications": unread_notifications
    }
