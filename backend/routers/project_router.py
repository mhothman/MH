"""Project management router - Refactored to use Repository pattern"""
from fastapi import APIRouter, HTTPException, Request
from datetime import datetime, timezone
from typing import Optional, List
import logging

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.database import get_database
from core.security import require_auth, require_permission, get_user_org_membership
from core.permissions import Permission
from models.enums import UserRole, ProjectStatus, TaskStatus
from models.project import ProjectCreate, ProjectUpdate, ProjectResponse
from repositories.project_repository import project_repository
from repositories.task_repository import task_repository
from repositories.customer_repository import customer_repository
from services.audit_service import audit_service
from services.notification_service import notification_service
from services.feature_service import feature_service

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/", response_model=List[ProjectResponse])
async def get_projects(request: Request, org_id: Optional[str] = None):
    """Get all projects user has access to"""
    db = get_database()
    user = await require_auth(request)
    
    if org_id:
        membership = await get_user_org_membership(user["user_id"], org_id)
        if not membership:
            raise HTTPException(status_code=403, detail="Access denied")
        projects = await project_repository.find_by_org(org_id)
    else:
        memberships = await db.org_memberships.find({"user_id": user["user_id"]}, {"_id": 0}).to_list(100)
        org_ids = [m["org_id"] for m in memberships]
        projects = await project_repository.find_all({"org_id": {"$in": org_ids}})
    
    # Get customer names in bulk
    customer_ids = list(set([p.get("customer_id") for p in projects if p.get("customer_id")]))
    customers_map = {}
    if customer_ids:
        for cid in customer_ids:
            customer = await customer_repository.find_by_id(cid)
            if customer:
                customers_map[cid] = customer["name"]
    
    # Get task counts in bulk using repository
    project_ids = [p["project_id"] for p in projects]
    task_counts_map = await task_repository.bulk_count_by_projects(project_ids)
    
    result = []
    for project in projects:
        counts = task_counts_map.get(project["project_id"], {"total": 0, "completed": 0})
        project["task_count"] = counts["total"]
        project["completed_tasks"] = counts["completed"]
        project["customer_name"] = customers_map.get(project.get("customer_id")) if project.get("customer_id") else None
        project["created_at"] = datetime.fromisoformat(project["created_at"]) if isinstance(project["created_at"], str) else project["created_at"]
        project["updated_at"] = datetime.fromisoformat(project.get("updated_at", project["created_at"])) if isinstance(project.get("updated_at", project["created_at"]), str) else project.get("updated_at", project["created_at"])
        
        result.append(ProjectResponse(**project))
    
    return result


@router.post("/", response_model=ProjectResponse)
async def create_project(data: ProjectCreate, request: Request, org_id: str):
    """Create a new project"""
    user = await require_permission(request, org_id, Permission.PROJECT_CREATE)
    
    # Check project limit
    current_projects = await project_repository.count_by_org(org_id)
    can_create = await feature_service.check_limit(org_id, "max_projects", current_projects)
    if not can_create:
        raise HTTPException(status_code=403, detail="Project limit reached for your plan")
    
    customer_name = None
    if data.customer_id and data.customer_id != "none":
        customer = await customer_repository.find_by_id(data.customer_id)
        if not customer or customer.get("org_id") != org_id:
            raise HTTPException(status_code=400, detail="Customer not found")
        customer_name = customer["name"]
    
    project_data = {
        "org_id": org_id,
        "name": data.name,
        "description": data.description,
        "status": data.status,
        "start_date": data.start_date,
        "end_date": data.end_date,
        "color": data.color,
        "customer_id": data.customer_id if data.customer_id != "none" else None,
        "owner_id": user["user_id"],
        "team_members": [user["user_id"]],
        "task_statuses": data.task_statuses or [
            {"id": "todo", "label": "To Do", "color": "#6B7280"},
            {"id": "in_progress", "label": "In Progress", "color": "#3B82F6"},
            {"id": "review", "label": "In Review", "color": "#F59E0B"},
            {"id": "done", "label": "Done", "color": "#10B981"}
        ],
    }
    
    project = await project_repository.create(project_data)
    
    await audit_service.log(user["user_id"], org_id, "create", "project", project["project_id"])
    
    project["task_count"] = 0
    project["completed_tasks"] = 0
    project["customer_name"] = customer_name
    project["created_at"] = datetime.fromisoformat(project["created_at"])
    project["updated_at"] = datetime.fromisoformat(project["updated_at"])
    
    return ProjectResponse(**project)


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: str, request: Request):
    """Get project by ID"""
    user = await require_auth(request)
    
    project = await project_repository.find_by_id(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    membership = await get_user_org_membership(user["user_id"], project["org_id"])
    if not membership:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Get task stats using repository
    stats = await task_repository.count_by_project(project_id)
    
    project["task_count"] = stats["total"]
    project["completed_tasks"] = stats["completed"]
    project["created_at"] = datetime.fromisoformat(project["created_at"]) if isinstance(project["created_at"], str) else project["created_at"]
    project["updated_at"] = datetime.fromisoformat(project.get("updated_at", project["created_at"])) if isinstance(project.get("updated_at"), str) else project.get("updated_at", project["created_at"])
    
    return ProjectResponse(**project)


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(project_id: str, data: ProjectUpdate, request: Request):
    """Update a project"""
    project = await project_repository.find_by_id(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    user = await require_permission(request, project["org_id"], Permission.PROJECT_EDIT)
    
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    
    # Handle customer_id "none" value
    if "customer_id" in update_data and update_data["customer_id"] == "none":
        update_data["customer_id"] = None
    
    if update_data:
        await project_repository.update(project_id, update_data)
    
    await audit_service.log(user["user_id"], project["org_id"], "update", "project", project_id, update_data)
    
    return await get_project(project_id, request)


@router.delete("/{project_id}")
async def delete_project(project_id: str, request: Request):
    """Delete/archive a project"""
    project = await project_repository.find_by_id(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    user = await require_permission(request, project["org_id"], Permission.PROJECT_DELETE)
    
    await project_repository.update(project_id, {"status": ProjectStatus.ARCHIVED})
    
    await audit_service.log(user["user_id"], project["org_id"], "archive", "project", project_id)
    
    return {"message": "Project archived successfully"}


@router.post("/{project_id}/members")
async def add_project_member(project_id: str, request: Request, user_id: str):
    """Add a member to project"""
    db = get_database()
    current_user = await require_auth(request)
    
    project = await project_repository.find_by_id(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    membership = await get_user_org_membership(current_user["user_id"], project["org_id"])
    if not membership or membership["role"] not in [UserRole.ORG_ADMIN, UserRole.PROJECT_MANAGER, UserRole.SUPER_ADMIN]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    target_membership = await get_user_org_membership(user_id, project["org_id"])
    if not target_membership:
        raise HTTPException(status_code=400, detail="User is not an organization member")
    
    # Add member to project's team_members array
    await db.projects.update_one(
        {"project_id": project_id},
        {"$addToSet": {"team_members": user_id}}
    )
    
    await notification_service.create(
        user_id,
        "project_added",
        "Added to project",
        f"You have been added to {project['name']}",
        f"/projects/{project_id}"
    )
    
    return {"message": "Member added successfully"}


@router.get("/{project_id}/members")
async def get_project_members(project_id: str, request: Request, include_all: bool = True):
    """Get project members with user details. By default includes all org members."""
    db = get_database()
    user = await require_auth(request)
    
    project = await project_repository.find_by_id(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    membership = await get_user_org_membership(user["user_id"], project["org_id"])
    if not membership:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Return all org members for the assignee dropdown using aggregation
    members = await db.org_memberships.aggregate([
        {"$match": {"org_id": project["org_id"]}},
        {"$lookup": {
            "from": "users",
            "localField": "user_id",
            "foreignField": "user_id",
            "as": "user"
        }},
        {"$unwind": "$user"},
        {"$project": {
            "_id": 0,
            "user_id": "$user.user_id",
            "name": {"$ifNull": ["$user.name", "Unknown"]},
            "email": {"$ifNull": ["$user.email", ""]},
            "picture": "$user.picture"
        }}
    ]).to_list(100)
    
    return members


@router.delete("/{project_id}/members/{user_id}")
async def remove_project_member(project_id: str, user_id: str, request: Request):
    """Remove a member from project"""
    db = get_database()
    current_user = await require_auth(request)
    
    project = await project_repository.find_by_id(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    membership = await get_user_org_membership(current_user["user_id"], project["org_id"])
    if not membership or membership["role"] not in [UserRole.ORG_ADMIN, UserRole.PROJECT_MANAGER, UserRole.SUPER_ADMIN]:
        raise HTTPException(status_code=403, detail="Access denied")
    
    if project.get("owner_id") == user_id:
        raise HTTPException(status_code=400, detail="Cannot remove project owner")
    
    await db.projects.update_one(
        {"project_id": project_id},
        {"$pull": {"team_members": user_id}}
    )
    
    return {"message": "Member removed successfully"}
