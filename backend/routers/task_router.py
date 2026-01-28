"""Task management router - Refactored to use TaskService"""
from fastapi import APIRouter, HTTPException, Request, UploadFile, File
from pydantic import BaseModel
from datetime import datetime, timezone
from typing import Optional, List
import logging

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.database import get_database
from core.security import require_auth, get_user_org_membership
from core.permissions import Permission, has_permission
from models.task import TaskCreate, TaskUpdate, SubtaskCreate, SubtaskUpdate
from repositories.project_repository import project_repository
from services.task_service import task_service

logger = logging.getLogger(__name__)
router = APIRouter()


# =============================================
# Task CRUD
# =============================================

@router.get("/")
async def get_tasks(
    request: Request,
    project_id: Optional[str] = None,
    status: Optional[str] = None,
    assignee_id: Optional[str] = None
):
    """Get tasks with optional filters"""
    db = get_database()
    user = await require_auth(request)
    
    if project_id:
        project = await project_repository.find_by_id(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        
        membership = await get_user_org_membership(user["user_id"], project["org_id"])
        if not membership:
            raise HTTPException(status_code=403, detail="Access denied")
        
        if not has_permission(membership["role"], Permission.TASK_VIEW):
            raise HTTPException(status_code=403, detail="Permission denied: cannot view tasks")
        
        return await task_service.get_tasks(project_id=project_id, status=status, assignee_id=assignee_id)
    else:
        memberships = await db.org_memberships.find({"user_id": user["user_id"]}, {"_id": 0}).to_list(100)
        org_ids = [m["org_id"] for m in memberships]
        project_ids = await project_repository.get_project_ids_for_orgs(org_ids)
        
        return await task_service.get_tasks(project_ids=project_ids, status=status, assignee_id=assignee_id)


@router.post("/")
async def create_task(data: TaskCreate, request: Request):
    """Create a new task"""
    user = await require_auth(request)
    
    project = await project_repository.find_by_id(data.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    membership = await get_user_org_membership(user["user_id"], project["org_id"])
    if not membership:
        raise HTTPException(status_code=403, detail="Access denied")
    
    if not has_permission(membership["role"], Permission.TASK_CREATE):
        raise HTTPException(status_code=403, detail="Permission denied: cannot create tasks")
    
    task = await task_service.create_task(
        user_id=user["user_id"],
        user_name=user["name"],
        project_id=data.project_id,
        org_id=project["org_id"],
        title=data.title,
        description=data.description,
        status=data.status,
        priority=data.priority,
        due_date=data.due_date,
        start_date=data.start_date,
        assignee_ids=data.assignee_ids,
        dependencies=data.dependencies,
        subtasks=[s.model_dump() for s in data.subtasks] if data.subtasks else None,
        estimated_hours=data.estimated_hours,
        recurring_rule=data.recurring_rule,
        baseline_start=data.baseline_start,
        baseline_end=data.baseline_end
    )
    
    # Trigger automation
    from routers.automation_router import automation_engine
    await automation_engine.trigger_event(
        project["org_id"],
        "task_created",
        {"task_id": task["task_id"], "project_id": data.project_id, "title": data.title, "status": data.status}
    )
    
    return task


@router.get("/{task_id}")
async def get_task(task_id: str, request: Request):
    """Get task by ID"""
    user = await require_auth(request)
    
    task = await task_service.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    membership = await get_user_org_membership(user["user_id"], task["org_id"])
    if not membership:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return task


@router.put("/{task_id}")
async def update_task(task_id: str, data: TaskUpdate, request: Request):
    """Update a task"""
    user = await require_auth(request)
    
    task = await task_service.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    membership = await get_user_org_membership(user["user_id"], task["org_id"])
    if not membership:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Check if task is locked pending approval
    if task.get("approval_locked", False):
        raise HTTPException(
            status_code=423,
            detail="Task is locked pending approval. Complete or cancel the approval first."
        )
    
    # Permission check
    can_edit_any = has_permission(membership["role"], Permission.TASK_EDIT)
    can_edit_own = has_permission(membership["role"], Permission.TASK_EDIT_OWN)
    is_assigned = user["user_id"] in task.get("assignee_ids", [])
    is_creator = task.get("created_by") == user["user_id"]
    
    if not can_edit_any and not (can_edit_own and (is_assigned or is_creator)):
        raise HTTPException(status_code=403, detail="Permission denied: cannot edit this task")
    
    old_status = task.get("status")
    old_priority = task.get("priority")
    
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    
    # Check if status change requires approval
    if "status" in update_data and update_data["status"] != old_status:
        from services.approval_service import approval_service
        requires_approval, rule, workflow = await approval_service.check_approval_required(
            task_id=task_id,
            from_status=old_status,
            to_status=update_data["status"]
        )
        
        if requires_approval:
            raise HTTPException(
                status_code=428,
                detail={
                    "message": "This status change requires approval",
                    "requires_approval": True,
                    "from_status": old_status,
                    "to_status": update_data["status"],
                    "rule": {
                        "rule_id": rule["rule_id"],
                        "approval_type": rule["approval_type"],
                        "approver_role": rule["approver_role"]
                    }
                }
            )
    
    success, message, updated_task = await task_service.update_task(task_id, user["user_id"], update_data)
    
    if not success:
        raise HTTPException(status_code=400, detail=message)
    
    # Trigger automations
    from routers.automation_router import automation_engine
    
    if "status" in update_data and update_data["status"] != old_status:
        await automation_engine.trigger_event(
            task["org_id"],
            "status_changed",
            {"task_id": task_id, "project_id": task["project_id"], "old_status": old_status, "new_status": update_data["status"]}
        )
    
    if "priority" in update_data and update_data["priority"] != old_priority:
        await automation_engine.trigger_event(
            task["org_id"],
            "priority_changed",
            {"task_id": task_id, "project_id": task["project_id"], "old_priority": old_priority, "new_priority": update_data["priority"]}
        )
    
    return updated_task


@router.delete("/{task_id}")
async def delete_task(task_id: str, request: Request):
    """Delete a task"""
    user = await require_auth(request)
    
    task = await task_service.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    membership = await get_user_org_membership(user["user_id"], task["org_id"])
    if not membership:
        raise HTTPException(status_code=403, detail="Access denied")
    
    if not has_permission(membership["role"], Permission.TASK_DELETE):
        raise HTTPException(status_code=403, detail="Permission denied: cannot delete tasks")
    
    success, message = await task_service.delete_task(task_id, user["user_id"])
    
    return {"message": message}


# =============================================
# Checklist Endpoints
# =============================================

@router.post("/{task_id}/checklist")
async def add_checklist_item(task_id: str, data: SubtaskCreate, request: Request):
    """Add a checklist item to a task"""
    user = await require_auth(request)
    
    task = await task_service.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    membership = await get_user_org_membership(user["user_id"], task["org_id"])
    if not membership:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return await task_service.add_checklist_item(task_id, data.title, data.completed)


@router.put("/{task_id}/checklist/{item_id}")
async def update_checklist_item(task_id: str, item_id: str, data: SubtaskUpdate, request: Request):
    """Update a checklist item"""
    user = await require_auth(request)
    
    task = await task_service.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    membership = await get_user_org_membership(user["user_id"], task["org_id"])
    if not membership:
        raise HTTPException(status_code=403, detail="Access denied")
    
    await task_service.update_checklist_item(task_id, item_id, data.title, data.completed)
    return {"message": "Checklist item updated"}


@router.delete("/{task_id}/checklist/{item_id}")
async def delete_checklist_item(task_id: str, item_id: str, request: Request):
    """Delete a checklist item"""
    user = await require_auth(request)
    
    task = await task_service.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    membership = await get_user_org_membership(user["user_id"], task["org_id"])
    if not membership:
        raise HTTPException(status_code=403, detail="Access denied")
    
    await task_service.delete_checklist_item(task_id, item_id)
    return {"message": "Checklist item deleted"}


# =============================================
# Dependencies
# =============================================

@router.put("/{task_id}/dependencies")
async def update_task_dependencies(task_id: str, request: Request, dependencies: List[str] = []):
    """Update task dependencies"""
    user = await require_auth(request)
    
    task = await task_service.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    membership = await get_user_org_membership(user["user_id"], task["org_id"])
    if not membership:
        raise HTTPException(status_code=403, detail="Access denied")
    
    await task_service.update_dependencies(task_id, dependencies)
    return {"message": "Dependencies updated"}


# =============================================
# Attachments
# =============================================

@router.post("/{task_id}/attachments")
async def upload_attachment(task_id: str, request: Request, file: UploadFile = File(...)):
    """Upload attachment to task"""
    user = await require_auth(request)
    
    task = await task_service.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    membership = await get_user_org_membership(user["user_id"], task["org_id"])
    if not membership:
        raise HTTPException(status_code=403, detail="Access denied")
    
    content = await file.read()
    return await task_service.upload_attachment(
        task_id=task_id,
        org_id=task["org_id"],
        user_id=user["user_id"],
        filename=file.filename,
        content=content,
        content_type=file.content_type
    )


@router.get("/{task_id}/attachments")
async def get_attachments(task_id: str, request: Request):
    """Get task attachments"""
    user = await require_auth(request)
    
    task = await task_service.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    membership = await get_user_org_membership(user["user_id"], task["org_id"])
    if not membership:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return await task_service.get_attachments(task_id)


@router.delete("/{task_id}/attachments/{attachment_id}")
async def delete_attachment(task_id: str, attachment_id: str, request: Request):
    """Delete an attachment"""
    user = await require_auth(request)
    
    task = await task_service.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    membership = await get_user_org_membership(user["user_id"], task["org_id"])
    if not membership:
        raise HTTPException(status_code=403, detail="Access denied")
    
    await task_service.delete_attachment(attachment_id)
    return {"message": "Attachment deleted"}


# =============================================
# Activity
# =============================================

@router.get("/{task_id}/activity")
async def get_task_activity(task_id: str, request: Request):
    """Get task activity log"""
    user = await require_auth(request)
    
    task = await task_service.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    membership = await get_user_org_membership(user["user_id"], task["org_id"])
    if not membership:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return await task_service.get_activity(task_id, task["org_id"])


# =============================================
# Bulk Operations
# =============================================

class BulkTaskUpdate(BaseModel):
    task_ids: List[str]
    updates: dict


class BulkTaskAssign(BaseModel):
    task_ids: List[str]
    assignee_id: str


class BulkTaskDelete(BaseModel):
    task_ids: List[str]


@router.post("/bulk/update")
async def bulk_update_tasks(data: BulkTaskUpdate, request: Request):
    """Bulk update multiple tasks"""
    from repositories.task_repository import task_repository
    
    user = await require_auth(request)
    
    if not data.task_ids:
        raise HTTPException(status_code=400, detail="No tasks specified")
    
    if len(data.task_ids) > 100:
        raise HTTPException(status_code=400, detail="Maximum 100 tasks per batch")
    
    # Permission check
    tasks = await task_repository.find_all({"task_id": {"$in": data.task_ids}})
    if not tasks:
        raise HTTPException(status_code=404, detail="No tasks found")
    
    org_ids = set(t["org_id"] for t in tasks)
    for org_id in org_ids:
        membership = await get_user_org_membership(user["user_id"], org_id)
        if not membership:
            raise HTTPException(status_code=403, detail="Access denied")
        if not has_permission(membership["role"], Permission.TASK_EDIT):
            raise HTTPException(status_code=403, detail="Permission denied: cannot edit tasks")
    
    success, modified_count = await task_service.bulk_update(data.task_ids, data.updates, user["user_id"])
    
    if not success:
        raise HTTPException(status_code=400, detail="No valid updates provided")
    
    return {"success": True, "modified_count": modified_count, "task_ids": data.task_ids}


@router.post("/bulk/assign")
async def bulk_assign_tasks(data: BulkTaskAssign, request: Request):
    """Bulk assign a user to multiple tasks"""
    from repositories.task_repository import task_repository
    
    user = await require_auth(request)
    
    if not data.task_ids:
        raise HTTPException(status_code=400, detail="No tasks specified")
    
    if len(data.task_ids) > 100:
        raise HTTPException(status_code=400, detail="Maximum 100 tasks per batch")
    
    # Permission check
    tasks = await task_repository.find_all({"task_id": {"$in": data.task_ids}})
    if not tasks:
        raise HTTPException(status_code=404, detail="No tasks found")
    
    org_ids = set(t["org_id"] for t in tasks)
    for org_id in org_ids:
        membership = await get_user_org_membership(user["user_id"], org_id)
        if not membership:
            raise HTTPException(status_code=403, detail="Access denied")
        if not has_permission(membership["role"], Permission.TASK_ASSIGN):
            raise HTTPException(status_code=403, detail="Permission denied: cannot assign tasks")
    
    success, modified_count = await task_service.bulk_assign(data.task_ids, data.assignee_id, user["user_id"])
    
    return {"success": True, "modified_count": modified_count, "assignee_id": data.assignee_id}


@router.post("/bulk/delete")
async def bulk_delete_tasks(data: BulkTaskDelete, request: Request):
    """Bulk delete multiple tasks"""
    from repositories.task_repository import task_repository
    
    user = await require_auth(request)
    
    if not data.task_ids:
        raise HTTPException(status_code=400, detail="No tasks specified")
    
    if len(data.task_ids) > 50:
        raise HTTPException(status_code=400, detail="Maximum 50 tasks per batch delete")
    
    # Permission check
    tasks = await task_repository.find_all({"task_id": {"$in": data.task_ids}})
    if not tasks:
        raise HTTPException(status_code=404, detail="No tasks found")
    
    org_ids = set(t["org_id"] for t in tasks)
    for org_id in org_ids:
        membership = await get_user_org_membership(user["user_id"], org_id)
        if not membership:
            raise HTTPException(status_code=403, detail="Access denied")
        if not has_permission(membership["role"], Permission.TASK_DELETE):
            raise HTTPException(status_code=403, detail="Permission denied: cannot delete tasks")
    
    success, deleted_count = await task_service.bulk_delete(data.task_ids, user["user_id"])
    
    return {"success": True, "deleted_count": deleted_count}
