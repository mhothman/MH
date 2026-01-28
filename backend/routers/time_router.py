"""Time tracking router - Refactored to use TimeService"""
from fastapi import APIRouter, HTTPException, Request
from datetime import datetime, timezone
from typing import Optional, List
import logging

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.database import get_database
from core.security import require_auth, get_user_org_membership
from core.permissions import Permission, has_permission
from services.time_service import time_service
from models.time_entry import TimeEntryCreate, TimerStart

logger = logging.getLogger(__name__)
router = APIRouter()


# =============================================
# Timer Endpoints
# =============================================

@router.post("/timer/start")
async def start_timer(data: TimerStart, request: Request):
    """Start a timer for a task"""
    db = get_database()
    user = await require_auth(request)
    
    task = await db.tasks.find_one({"task_id": data.task_id}, {"_id": 0})
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    membership = await get_user_org_membership(user["user_id"], task["org_id"])
    if not membership:
        raise HTTPException(status_code=403, detail="Access denied")
    
    if not has_permission(membership["role"], Permission.TIME_CREATE):
        raise HTTPException(status_code=403, detail="Permission denied: cannot track time")
    
    success, message, timer = await time_service.start_timer(
        user_id=user["user_id"],
        task_id=data.task_id,
        org_id=task["org_id"],
        description=data.description
    )
    
    if not success:
        raise HTTPException(status_code=400, detail=message)
    
    return timer


@router.post("/timer/stop")
async def stop_timer(request: Request):
    """Stop the active timer and create a time entry"""
    user = await require_auth(request)
    
    success, message, result = await time_service.stop_timer(user["user_id"])
    
    if not success:
        raise HTTPException(status_code=404, detail=message)
    
    return {"message": message, **result}


@router.get("/timer/active")
async def get_active_timer(request: Request):
    """Get the user's active timer"""
    user = await require_auth(request)
    
    timer = await time_service.get_active_timer(user["user_id"])
    
    if not timer:
        return {"active": False, "timer": None}
    
    return {"active": True, "timer": timer}


@router.delete("/timer/discard")
async def discard_timer(request: Request):
    """Discard the active timer without creating a time entry"""
    user = await require_auth(request)
    
    success = await time_service.discard_timer(user["user_id"])
    
    if not success:
        raise HTTPException(status_code=404, detail="No active timer found")
    
    return {"message": "Timer discarded"}


# =============================================
# Time Entry Endpoints
# =============================================

@router.get("/")
async def get_time_entries(
    request: Request,
    task_id: Optional[str] = None,
    project_id: Optional[str] = None,
    user_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = 100
):
    """Get time entries with optional filters"""
    db = get_database()
    user = await require_auth(request)
    
    task_ids = None
    
    if task_id:
        task = await db.tasks.find_one({"task_id": task_id}, {"_id": 0})
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        
        membership = await get_user_org_membership(user["user_id"], task["org_id"])
        if not membership:
            raise HTTPException(status_code=403, detail="Access denied")
        
        return await time_service.get_entries(
            task_id=task_id,
            start_date=start_date,
            end_date=end_date,
            limit=limit
        )
    elif project_id:
        project = await db.projects.find_one({"project_id": project_id}, {"_id": 0})
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        membership = await get_user_org_membership(user["user_id"], project["org_id"])
        if not membership:
            raise HTTPException(status_code=403, detail="Access denied")
        
        tasks = await db.tasks.find({"project_id": project_id}, {"task_id": 1}).to_list(None)
        task_ids = [t["task_id"] for t in tasks]
        
        return await time_service.get_entries(
            task_ids=task_ids,
            start_date=start_date,
            end_date=end_date,
            limit=limit
        )
    else:
        query_user_id = user_id or user["user_id"]
        return await time_service.get_entries(
            user_id=query_user_id,
            start_date=start_date,
            end_date=end_date,
            limit=limit
        )


@router.post("/")
async def create_time_entry(data: TimeEntryCreate, request: Request):
    """Create a manual time entry"""
    db = get_database()
    user = await require_auth(request)
    
    task = await db.tasks.find_one({"task_id": data.task_id}, {"_id": 0})
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    membership = await get_user_org_membership(user["user_id"], task["org_id"])
    if not membership:
        raise HTTPException(status_code=403, detail="Access denied")
    
    if not has_permission(membership["role"], Permission.TIME_CREATE):
        raise HTTPException(status_code=403, detail="Permission denied: cannot create time entries")
    
    return await time_service.create_entry(
        user_id=user["user_id"],
        task_id=data.task_id,
        org_id=task["org_id"],
        duration_minutes=data.duration_minutes,
        description=data.description,
        date=data.date
    )


@router.put("/{entry_id}")
async def update_time_entry(entry_id: str, data: TimeEntryCreate, request: Request):
    """Update a time entry"""
    user = await require_auth(request)
    
    entry = await time_service.get_entry(entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Time entry not found")
    
    if entry["user_id"] != user["user_id"]:
        raise HTTPException(status_code=403, detail="You can only edit your own time entries")
    
    membership = await get_user_org_membership(user["user_id"], entry["org_id"])
    if not membership:
        raise HTTPException(status_code=403, detail="Access denied")
    
    if not has_permission(membership["role"], Permission.TIME_EDIT_OWN):
        raise HTTPException(status_code=403, detail="Permission denied: cannot edit time entries")
    
    success, message = await time_service.update_entry(
        entry_id=entry_id,
        duration_minutes=data.duration_minutes,
        description=data.description,
        date=data.date
    )
    
    if not success:
        raise HTTPException(status_code=404, detail=message)
    
    return {"message": message}


@router.delete("/{entry_id}")
async def delete_time_entry(entry_id: str, request: Request):
    """Delete a time entry"""
    user = await require_auth(request)
    
    entry = await time_service.get_entry(entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Time entry not found")
    
    if entry["user_id"] != user["user_id"]:
        raise HTTPException(status_code=403, detail="You can only delete your own time entries")
    
    membership = await get_user_org_membership(user["user_id"], entry["org_id"])
    if not membership:
        raise HTTPException(status_code=403, detail="Access denied")
    
    if not has_permission(membership["role"], Permission.TIME_EDIT_OWN):
        raise HTTPException(status_code=403, detail="Permission denied: cannot delete time entries")
    
    success, message = await time_service.delete_entry(entry_id)
    
    if not success:
        raise HTTPException(status_code=404, detail=message)
    
    return {"message": message}


@router.get("/summary")
async def get_time_summary(
    request: Request,
    project_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    """Get time summary by user and task"""
    db = get_database()
    user = await require_auth(request)
    
    task_ids = None
    
    if project_id:
        project = await db.projects.find_one({"project_id": project_id}, {"_id": 0})
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        membership = await get_user_org_membership(user["user_id"], project["org_id"])
        if not membership:
            raise HTTPException(status_code=403, detail="Access denied")
        
        tasks = await db.tasks.find({"project_id": project_id}, {"task_id": 1}).to_list(None)
        task_ids = [t["task_id"] for t in tasks]
    
    return await time_service.get_summary(
        user_id=user["user_id"] if not task_ids else None,
        task_ids=task_ids,
        start_date=start_date,
        end_date=end_date
    )
