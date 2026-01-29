"""
Workflow Router - API endpoints for organization-scoped task approval workflows

Endpoints:
- Organization-level Workflow CRUD
- Workflow Rule CRUD  
- Project assignment management
- Approval request and actions
- Approval queries
"""
from fastapi import APIRouter, HTTPException, Request
from typing import Optional, List
import logging

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.database import get_database
from core.security import require_auth, get_user_org_membership
from core.permissions import Permission, has_permission
from models.workflow import (
    TaskWorkflowCreate, TaskWorkflowUpdate, TaskWorkflowResponse,
    TaskWorkflowRuleCreate, TaskWorkflowRuleUpdate, TaskWorkflowRuleResponse,
    TaskApprovalActionCreate, TaskApprovalResponse,
    RequestApprovalInput, WorkflowProjectAssignment, WorkflowScope
)
from repositories.workflow_repository import workflow_repository
from repositories.project_repository import project_repository
from services.approval_service import approval_service

logger = logging.getLogger(__name__)
router = APIRouter()


# ==================== Organization Workflow CRUD ====================

# NOTE: Static routes must come before dynamic routes to avoid matching issues
# The /pending route must be defined before /{workflow_id}

@router.get("/pending")
async def get_pending_approvals(request: Request, org_id: Optional[str] = None):
    """Get pending approvals for the current user"""
    user = await require_auth(request)
    db = get_database()
    
    if org_id:
        membership = await get_user_org_membership(user["user_id"], org_id)
        if not membership:
            raise HTTPException(status_code=403, detail="Access denied")
        
        approvals = await approval_service.get_pending_approvals_for_user(
            user_id=user["user_id"],
            org_id=org_id
        )
    else:
        memberships = await db.org_memberships.find(
            {"user_id": user["user_id"]},
            {"_id": 0, "org_id": 1}
        ).to_list(100)
        
        approvals = []
        for mem in memberships:
            org_approvals = await approval_service.get_pending_approvals_for_user(
                user_id=user["user_id"],
                org_id=mem["org_id"]
            )
            approvals.extend(org_approvals)
    
    # Enrich with task and project info
    enriched = []
    from repositories.task_repository import task_repository
    for approval in approvals:
        task = await task_repository.find_by_id(approval["task_id"])
        project = await project_repository.find_by_id(approval["project_id"])
        requester = await db.users.find_one(
            {"user_id": approval["requested_by"]},
            {"_id": 0, "name": 1}
        )
        
        enriched.append({
            **approval,
            "task_title": task.get("title") if task else "Unknown",
            "project_name": project.get("name") if project else "Unknown",
            "requester_name": requester.get("name") if requester else "Unknown"
        })
    
    return enriched


@router.post("/org/{org_id}", response_model=TaskWorkflowResponse)
async def create_workflow(org_id: str, data: TaskWorkflowCreate, request: Request):
    """Create a new workflow for an organization"""
    user = await require_auth(request)
    
    membership = await get_user_org_membership(user["user_id"], org_id)
    if not membership:
        raise HTTPException(status_code=403, detail="Access denied")
    
    if not has_permission(membership["role"], Permission.WORKFLOW_CREATE):
        raise HTTPException(status_code=403, detail="Permission denied: cannot create workflows")
    
    success, workflow, message = await approval_service.create_workflow(
        org_id=org_id,
        name=data.name,
        description=data.description,
        scope=data.scope.value if hasattr(data.scope, 'value') else data.scope,
        created_by=user["user_id"]
    )
    
    if not success:
        raise HTTPException(status_code=400, detail=message)
    
    workflow["rules_count"] = 0
    workflow["assigned_projects_count"] = 0
    workflow["assigned_projects"] = []
    
    return workflow


@router.get("/org/{org_id}")
async def get_org_workflows(org_id: str, request: Request, active_only: bool = False, include_rules: bool = True):
    """Get all workflows for an organization"""
    user = await require_auth(request)
    
    membership = await get_user_org_membership(user["user_id"], org_id)
    if not membership:
        raise HTTPException(status_code=403, detail="Access denied")
    
    if not has_permission(membership["role"], Permission.WORKFLOW_VIEW):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    workflows = await workflow_repository.find_by_org(org_id, active_only=active_only)
    
    # Enrich with counts and optionally rules
    for wf in workflows:
        if include_rules:
            rules = await workflow_repository.get_rules_by_workflow(wf["workflow_id"])
            wf["rules"] = rules
            wf["rules_count"] = len(rules)
        else:
            wf["rules_count"] = await workflow_repository.count_rules_by_workflow(wf["workflow_id"])
        
        if wf.get("scope") == "selective":
            wf["assigned_projects_count"] = await workflow_repository.count_assigned_projects(wf["workflow_id"])
            assignments = await workflow_repository.get_assigned_projects(wf["workflow_id"])
            wf["assigned_projects"] = [a["project_id"] for a in assignments]
        else:
            wf["assigned_projects_count"] = 0
            wf["assigned_projects"] = []
    
    return workflows


@router.get("/{workflow_id}")
async def get_workflow(workflow_id: str, request: Request):
    """Get a workflow with its rules"""
    user = await require_auth(request)
    
    workflow = await workflow_repository.get_workflow_with_rules(workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    membership = await get_user_org_membership(user["user_id"], workflow["org_id"])
    if not membership:
        raise HTTPException(status_code=403, detail="Access denied")
    
    if not has_permission(membership["role"], Permission.WORKFLOW_VIEW):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    return workflow


@router.put("/{workflow_id}")
async def update_workflow(workflow_id: str, data: TaskWorkflowUpdate, request: Request):
    """Update a workflow"""
    user = await require_auth(request)
    
    workflow = await workflow_repository.find_by_id(workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    membership = await get_user_org_membership(user["user_id"], workflow["org_id"])
    if not membership:
        raise HTTPException(status_code=403, detail="Access denied")
    
    if not has_permission(membership["role"], Permission.WORKFLOW_EDIT):
        raise HTTPException(status_code=403, detail="Permission denied: cannot edit workflows")
    
    updates = {}
    for k, v in data.model_dump().items():
        if v is not None:
            if hasattr(v, 'value'):
                updates[k] = v.value
            else:
                updates[k] = v
    
    if not updates:
        raise HTTPException(status_code=400, detail="No updates provided")
    
    success, updated, message = await approval_service.update_workflow(
        workflow_id=workflow_id,
        updates=updates,
        updated_by=user["user_id"],
        org_id=workflow["org_id"]
    )
    
    if not success:
        raise HTTPException(status_code=400, detail=message)
    
    return updated


@router.delete("/{workflow_id}")
async def delete_workflow(workflow_id: str, request: Request):
    """Delete a workflow and its rules"""
    user = await require_auth(request)
    
    workflow = await workflow_repository.find_by_id(workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    membership = await get_user_org_membership(user["user_id"], workflow["org_id"])
    if not membership:
        raise HTTPException(status_code=403, detail="Access denied")
    
    if not has_permission(membership["role"], Permission.WORKFLOW_DELETE):
        raise HTTPException(status_code=403, detail="Permission denied: cannot delete workflows")
    
    success, message = await approval_service.delete_workflow(
        workflow_id=workflow_id,
        deleted_by=user["user_id"],
        org_id=workflow["org_id"]
    )
    
    if not success:
        raise HTTPException(status_code=400, detail=message)
    
    return {"message": message}


# ==================== Project Assignment ====================

@router.put("/{workflow_id}/projects")
async def assign_projects_to_workflow(
    workflow_id: str, 
    data: WorkflowProjectAssignment, 
    request: Request
):
    """Assign projects to a selective workflow"""
    user = await require_auth(request)
    
    workflow = await workflow_repository.find_by_id(workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    membership = await get_user_org_membership(user["user_id"], workflow["org_id"])
    if not membership:
        raise HTTPException(status_code=403, detail="Access denied")
    
    if not has_permission(membership["role"], Permission.WORKFLOW_EDIT):
        raise HTTPException(status_code=403, detail="Permission denied: cannot assign projects")
    
    success, message = await approval_service.assign_projects_to_workflow(
        workflow_id=workflow_id,
        project_ids=data.project_ids,
        assigned_by=user["user_id"],
        org_id=workflow["org_id"]
    )
    
    if not success:
        raise HTTPException(status_code=400, detail=message)
    
    return {"message": message, "assigned_projects": data.project_ids}


@router.get("/{workflow_id}/projects")
async def get_workflow_projects(workflow_id: str, request: Request):
    """Get projects assigned to a workflow"""
    user = await require_auth(request)
    
    workflow = await workflow_repository.find_by_id(workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    membership = await get_user_org_membership(user["user_id"], workflow["org_id"])
    if not membership:
        raise HTTPException(status_code=403, detail="Access denied")
    
    assignments = await workflow_repository.get_assigned_projects(workflow_id)
    
    # Enrich with project names
    enriched = []
    for assignment in assignments:
        project = await project_repository.find_by_id(assignment["project_id"])
        assignment["project_name"] = project.get("name") if project else "Unknown"
        enriched.append(assignment)
    
    return enriched


# ==================== Project View (Read-Only) ====================

@router.get("/projects/{project_id}/applicable")
async def get_applicable_workflows_for_project(project_id: str, request: Request):
    """Get workflows that apply to a project (read-only view for Project Managers)"""
    user = await require_auth(request)
    
    project = await project_repository.find_by_id(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    membership = await get_user_org_membership(user["user_id"], project["org_id"])
    if not membership:
        raise HTTPException(status_code=403, detail="Access denied")
    
    result = await approval_service.get_project_applicable_workflows(
        project_id=project_id,
        org_id=project["org_id"]
    )
    
    return result


# ==================== Workflow Rule CRUD ====================

@router.post("/{workflow_id}/rules", response_model=TaskWorkflowRuleResponse)
async def create_workflow_rule(workflow_id: str, data: TaskWorkflowRuleCreate, request: Request):
    """Create a workflow rule"""
    user = await require_auth(request)
    
    workflow = await workflow_repository.find_by_id(workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    membership = await get_user_org_membership(user["user_id"], workflow["org_id"])
    if not membership:
        raise HTTPException(status_code=403, detail="Access denied")
    
    if not has_permission(membership["role"], Permission.WORKFLOW_EDIT):
        raise HTTPException(status_code=403, detail="Permission denied: cannot create workflow rules")
    
    success, rule, message = await approval_service.create_rule(
        workflow_id=workflow_id,
        from_status=data.from_status,
        to_status=data.to_status,
        description=data.description,
        approval_required=data.approval_required,
        approval_type=data.approval_type.value if hasattr(data.approval_type, 'value') else data.approval_type,
        approver_role=data.approver_role.value if hasattr(data.approver_role, 'value') else data.approver_role,
        approval_timeout_minutes=data.approval_timeout_minutes,
        auto_approve_on_timeout=data.auto_approve_on_timeout,
        created_by=user["user_id"],
        org_id=workflow["org_id"],
        notify_on_request=data.notify_on_request,
        notify_on_resolution=data.notify_on_resolution
    )
    
    if not success:
        raise HTTPException(status_code=400, detail=message)
    
    return rule


@router.get("/{workflow_id}/rules")
async def get_workflow_rules(workflow_id: str, request: Request):
    """Get all rules for a workflow"""
    user = await require_auth(request)
    
    workflow = await workflow_repository.find_by_id(workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    membership = await get_user_org_membership(user["user_id"], workflow["org_id"])
    if not membership:
        raise HTTPException(status_code=403, detail="Access denied")
    
    if not has_permission(membership["role"], Permission.WORKFLOW_VIEW):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    return await workflow_repository.find_rules_by_workflow(workflow_id)


@router.put("/rules/{rule_id}")
async def update_workflow_rule(rule_id: str, data: TaskWorkflowRuleUpdate, request: Request):
    """Update a workflow rule"""
    user = await require_auth(request)
    
    rule = await workflow_repository.find_rule_by_id(rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    
    workflow = await workflow_repository.find_by_id(rule["workflow_id"])
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    membership = await get_user_org_membership(user["user_id"], workflow["org_id"])
    if not membership:
        raise HTTPException(status_code=403, detail="Access denied")
    
    if not has_permission(membership["role"], Permission.WORKFLOW_EDIT):
        raise HTTPException(status_code=403, detail="Permission denied: cannot edit workflow rules")
    
    updates = {}
    for k, v in data.model_dump().items():
        if v is not None:
            if hasattr(v, 'value'):
                updates[k] = v.value
            else:
                updates[k] = v
    
    if not updates:
        raise HTTPException(status_code=400, detail="No updates provided")
    
    success, updated, message = await approval_service.update_rule(
        rule_id=rule_id,
        updates=updates,
        updated_by=user["user_id"],
        org_id=workflow["org_id"]
    )
    
    if not success:
        raise HTTPException(status_code=400, detail=message)
    
    return updated


@router.delete("/rules/{rule_id}")
async def delete_workflow_rule(rule_id: str, request: Request):
    """Delete a workflow rule"""
    user = await require_auth(request)
    
    rule = await workflow_repository.find_rule_by_id(rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    
    workflow = await workflow_repository.find_by_id(rule["workflow_id"])
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    membership = await get_user_org_membership(user["user_id"], workflow["org_id"])
    if not membership:
        raise HTTPException(status_code=403, detail="Access denied")
    
    if not has_permission(membership["role"], Permission.WORKFLOW_EDIT):
        raise HTTPException(status_code=403, detail="Permission denied: cannot delete workflow rules")
    
    success, message = await approval_service.delete_rule(
        rule_id=rule_id,
        deleted_by=user["user_id"],
        org_id=workflow["org_id"]
    )
    
    if not success:
        raise HTTPException(status_code=400, detail=message)
    
    return {"message": message}


# ==================== Approval Actions ====================

@router.post("/tasks/{task_id}/request-approval")
async def request_task_approval(task_id: str, data: RequestApprovalInput, request: Request):
    """Request approval for a task status change"""
    user = await require_auth(request)
    
    from repositories.task_repository import task_repository
    task = await task_repository.find_by_id(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    membership = await get_user_org_membership(user["user_id"], task["org_id"])
    if not membership:
        raise HTTPException(status_code=403, detail="Access denied")
    
    if not has_permission(membership["role"], Permission.APPROVAL_REQUEST):
        raise HTTPException(status_code=403, detail="Permission denied: cannot request approvals")
    
    success, approval, message = await approval_service.request_approval(
        task_id=task_id,
        target_status=data.target_status,
        requested_by=user["user_id"],
        org_id=task["org_id"],
        comment=data.comment
    )
    
    if not success:
        raise HTTPException(status_code=400, detail=message)
    
    return {"message": message, "approval": approval}


@router.post("/approvals/{approval_id}/approve")
async def approve_request(approval_id: str, data: TaskApprovalActionCreate, request: Request):
    """Approve an approval request"""
    user = await require_auth(request)
    
    approval = await workflow_repository.find_approval_by_id(approval_id)
    if not approval:
        raise HTTPException(status_code=404, detail="Approval not found")
    
    membership = await get_user_org_membership(user["user_id"], approval["org_id"])
    if not membership:
        raise HTTPException(status_code=403, detail="Access denied")
    
    is_force = data.action.value in ["force_approve", "force_reject"]
    
    if is_force:
        if not has_permission(membership["role"], Permission.APPROVAL_FORCE):
            raise HTTPException(status_code=403, detail="Permission denied: cannot force approve")
    else:
        if not has_permission(membership["role"], Permission.APPROVAL_APPROVE):
            raise HTTPException(status_code=403, detail="Permission denied: cannot approve")
    
    success, message = await approval_service.approve(
        approval_id=approval_id,
        acted_by=user["user_id"],
        org_id=approval["org_id"],
        comment=data.comment,
        is_force=is_force
    )
    
    if not success:
        raise HTTPException(status_code=400, detail=message)
    
    return {"message": message}


@router.post("/approvals/{approval_id}/reject")
async def reject_request(approval_id: str, data: TaskApprovalActionCreate, request: Request):
    """Reject an approval request"""
    user = await require_auth(request)
    
    approval = await workflow_repository.find_approval_by_id(approval_id)
    if not approval:
        raise HTTPException(status_code=404, detail="Approval not found")
    
    membership = await get_user_org_membership(user["user_id"], approval["org_id"])
    if not membership:
        raise HTTPException(status_code=403, detail="Access denied")
    
    is_force = data.action.value in ["force_approve", "force_reject"]
    
    if is_force:
        if not has_permission(membership["role"], Permission.APPROVAL_FORCE):
            raise HTTPException(status_code=403, detail="Permission denied: cannot force reject")
    else:
        if not has_permission(membership["role"], Permission.APPROVAL_REJECT):
            raise HTTPException(status_code=403, detail="Permission denied: cannot reject")
    
    success, message = await approval_service.reject(
        approval_id=approval_id,
        acted_by=user["user_id"],
        org_id=approval["org_id"],
        comment=data.comment,
        is_force=is_force
    )
    
    if not success:
        raise HTTPException(status_code=400, detail=message)
    
    return {"message": message}


# ==================== Approval Queries ====================

@router.get("/tasks/{task_id}/approval-summary")
async def get_task_approval_summary(task_id: str, request: Request):
    """Get approval summary for a task"""
    user = await require_auth(request)
    
    from repositories.task_repository import task_repository
    task = await task_repository.find_by_id(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    membership = await get_user_org_membership(user["user_id"], task["org_id"])
    if not membership:
        raise HTTPException(status_code=403, detail="Access denied")
    
    if not has_permission(membership["role"], Permission.APPROVAL_VIEW):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    summary = await approval_service.get_task_approval_summary(
        task_id=task_id,
        user_id=user["user_id"],
        org_id=task["org_id"]
    )
    
    return summary


@router.get("/org/{org_id}/approvals")
async def get_org_approvals(
    org_id: str,
    request: Request,
    status: Optional[str] = None,
    limit: int = 50
):
    """Get all approvals for an organization"""
    user = await require_auth(request)
    
    membership = await get_user_org_membership(user["user_id"], org_id)
    if not membership:
        raise HTTPException(status_code=403, detail="Access denied")
    
    if not has_permission(membership["role"], Permission.APPROVAL_VIEW):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    approvals = await workflow_repository.find_approvals_by_org(
        org_id=org_id,
        status=status,
        limit=limit
    )
    
    # Enrich with task info
    db = get_database()
    from repositories.task_repository import task_repository
    
    enriched = []
    for approval in approvals:
        task = await task_repository.find_by_id(approval["task_id"])
        project = await project_repository.find_by_id(approval["project_id"])
        requester = await db.users.find_one(
            {"user_id": approval["requested_by"]},
            {"_id": 0, "name": 1}
        )
        
        enriched.append({
            **approval,
            "task_title": task.get("title") if task else "Unknown",
            "project_name": project.get("name") if project else "Unknown",
            "requester_name": requester.get("name") if requester else "Unknown"
        })
    
    return enriched


@router.get("/approvals/{approval_id}")
async def get_approval_detail(approval_id: str, request: Request):
    """Get detailed approval info with actions"""
    user = await require_auth(request)
    
    approval = await workflow_repository.get_approval_with_actions(approval_id)
    if not approval:
        raise HTTPException(status_code=404, detail="Approval not found")
    
    membership = await get_user_org_membership(user["user_id"], approval["org_id"])
    if not membership:
        raise HTTPException(status_code=403, detail="Access denied")
    
    if not has_permission(membership["role"], Permission.APPROVAL_VIEW):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    # Enrich actions with actor names
    db = get_database()
    for action in approval.get("actions", []):
        if action["acted_by"] != "system":
            actor = await db.users.find_one(
                {"user_id": action["acted_by"]},
                {"_id": 0, "name": 1}
            )
            action["actor_name"] = actor.get("name") if actor else "Unknown"
        else:
            action["actor_name"] = "System"
    
    return approval


# ==================== Check Approval Required ====================

@router.get("/tasks/{task_id}/check-approval")
async def check_approval_required(task_id: str, target_status: str, request: Request):
    """Check if a status change requires approval"""
    user = await require_auth(request)
    
    from repositories.task_repository import task_repository
    task = await task_repository.find_by_id(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    membership = await get_user_org_membership(user["user_id"], task["org_id"])
    if not membership:
        raise HTTPException(status_code=403, detail="Access denied")
    
    requires_approval, rule, workflow = await approval_service.check_approval_required(
        task_id=task_id,
        from_status=task["status"],
        to_status=target_status
    )
    
    return {
        "requires_approval": requires_approval,
        "current_status": task["status"],
        "target_status": target_status,
        "rule": rule,
        "workflow": {
            "workflow_id": workflow["workflow_id"],
            "name": workflow["name"],
            "scope": workflow.get("scope", "selective")
        } if workflow else None
    }


# ==================== Migration Endpoint ====================

@router.post("/migrate/{org_id}")
async def migrate_workflows(org_id: str, request: Request):
    """Migrate old project-level workflows to org-level (admin only)"""
    user = await require_auth(request)
    
    membership = await get_user_org_membership(user["user_id"], org_id)
    if not membership or membership["role"] not in ["org_admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    count = await approval_service.migrate_existing_workflows(org_id)
    
    return {"message": f"Migrated {count} workflow(s) to organization level"}
