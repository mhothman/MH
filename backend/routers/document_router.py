"""
Document Router - API endpoints for documents and document approval workflows

Endpoints:
- Document CRUD
- Document Workflow CRUD
- Document Workflow Rules CRUD
- Document Approval Request and Actions
- Document Approval Queries
- Document Attachments
- Document Version History
"""
from fastapi import APIRouter, HTTPException, Request, UploadFile, File
from typing import Optional, List
import logging
import os
import uuid
from datetime import datetime, timezone

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.database import get_database
from core.security import require_auth, get_user_org_membership
from core.permissions import Permission, has_permission
from models.document import (
    DocumentCreate, DocumentUpdate, DocumentResponse, DocumentStatusChange,
    DocumentWorkflowCreate, DocumentWorkflowUpdate, DocumentWorkflowResponse,
    DocumentWorkflowRuleCreate, DocumentWorkflowRuleUpdate, DocumentWorkflowRuleResponse,
    DocumentApprovalActionCreate, RequestDocApprovalInput,
    DocumentAttachmentCreate, DocumentAttachmentResponse, DocumentVersionResponse,
    DocumentStatus, DocumentType
)
from repositories.document_repository import (
    document_repository, document_workflow_repository,
    document_attachment_repository, document_version_repository
)
from repositories.project_repository import project_repository
from services.document_approval_service import document_approval_service

logger = logging.getLogger(__name__)
router = APIRouter()

# Upload directory for document attachments
UPLOAD_DIR = os.environ.get("DOCUMENT_UPLOAD_DIR", "/app/uploads/documents")
os.makedirs(UPLOAD_DIR, exist_ok=True)


# ==================== Document Endpoints ====================

@router.post("/", response_model=DocumentResponse)
async def create_document(data: DocumentCreate, request: Request, org_id: str):
    """Create a new document"""
    user = await require_auth(request)
    
    membership = await get_user_org_membership(user["user_id"], org_id)
    if not membership:
        raise HTTPException(status_code=403, detail="Access denied")
    
    if not has_permission(membership["role"], Permission.DOCUMENT_CREATE):
        raise HTTPException(status_code=403, detail="Permission denied: cannot create documents")
    
    success, document, message = await document_approval_service.create_document(
        org_id=org_id,
        title=data.title,
        created_by=user["user_id"],
        document_type=data.document_type.value if hasattr(data.document_type, 'value') else data.document_type,
        description=data.description,
        project_id=data.project_id,
        content=data.content,
        file_url=data.file_url,
        metadata=data.metadata,
        tags=data.tags
    )
    
    if not success:
        raise HTTPException(status_code=400, detail=message)
    
    return document


@router.get("/")
async def get_documents(
    request: Request,
    org_id: str,
    project_id: Optional[str] = None,
    document_type: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
):
    """Get documents with filters"""
    user = await require_auth(request)
    
    membership = await get_user_org_membership(user["user_id"], org_id)
    if not membership:
        raise HTTPException(status_code=403, detail="Access denied")
    
    if not has_permission(membership["role"], Permission.DOCUMENT_VIEW):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    documents = await document_repository.find_by_org(
        org_id=org_id,
        project_id=project_id,
        document_type=document_type,
        status=status,
        search=search,
        limit=limit,
        offset=offset
    )
    
    # Enrich with owner and project names
    db = get_database()
    for doc in documents:
        owner = await db.users.find_one(
            {"user_id": doc["owner_id"]},
            {"_id": 0, "name": 1}
        )
        doc["owner_name"] = owner.get("name") if owner else "Unknown"
        
        if doc.get("project_id"):
            project = await project_repository.find_by_id(doc["project_id"])
            doc["project_name"] = project.get("name") if project else "Unknown"
    
    return documents


@router.get("/types")
async def get_document_types():
    """Get available document types"""
    return [
        {"value": t.value, "label": t.value.replace("_", " ").title()}
        for t in DocumentType
    ]


@router.get("/statuses")
async def get_document_statuses():
    """Get available document statuses"""
    return [
        {"value": s.value, "label": s.value.replace("_", " ").title()}
        for s in DocumentStatus
    ]


@router.get("/org/{org_id}/approvals")
async def get_org_document_approvals(
    org_id: str,
    request: Request,
    status: Optional[str] = None,
    limit: int = 50
):
    """Get all document approvals for an organization"""
    user = await require_auth(request)
    
    membership = await get_user_org_membership(user["user_id"], org_id)
    if not membership:
        raise HTTPException(status_code=403, detail="Access denied")
    
    if not has_permission(membership["role"], Permission.APPROVAL_VIEW):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    approvals = await document_workflow_repository.find_approvals_by_org(
        org_id=org_id,
        status=status,
        limit=limit
    )
    
    # Enrich with document info
    db = get_database()
    enriched = []
    for approval in approvals:
        document = await document_repository.find_by_id(approval["document_id"])
        requester = await db.users.find_one(
            {"user_id": approval["requested_by"]},
            {"_id": 0, "name": 1}
        )
        
        enriched.append({
            **approval,
            "document_title": document.get("title") if document else "Unknown",
            "project_id": document.get("project_id") if document else None,
            "requester_name": requester.get("name") if requester else "Unknown"
        })
    
    return enriched


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(document_id: str, request: Request):
    """Get a document by ID"""
    user = await require_auth(request)
    
    document = await document_repository.find_by_id(document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    membership = await get_user_org_membership(user["user_id"], document["org_id"])
    if not membership:
        raise HTTPException(status_code=403, detail="Access denied")
    
    if not has_permission(membership["role"], Permission.DOCUMENT_VIEW):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    # Enrich
    db = get_database()
    owner = await db.users.find_one(
        {"user_id": document["owner_id"]},
        {"_id": 0, "name": 1}
    )
    document["owner_name"] = owner.get("name") if owner else "Unknown"
    
    if document.get("project_id"):
        project = await project_repository.find_by_id(document["project_id"])
        document["project_name"] = project.get("name") if project else "Unknown"
    
    return document


@router.put("/{document_id}", response_model=DocumentResponse)
async def update_document(document_id: str, data: DocumentUpdate, request: Request):
    """Update a document"""
    user = await require_auth(request)
    
    document = await document_repository.find_by_id(document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    membership = await get_user_org_membership(user["user_id"], document["org_id"])
    if not membership:
        raise HTTPException(status_code=403, detail="Access denied")
    
    if not has_permission(membership["role"], Permission.DOCUMENT_EDIT):
        raise HTTPException(status_code=403, detail="Permission denied: cannot edit documents")
    
    updates = {}
    for k, v in data.model_dump().items():
        if v is not None:
            if hasattr(v, 'value'):
                updates[k] = v.value
            else:
                updates[k] = v
    
    if not updates:
        raise HTTPException(status_code=400, detail="No updates provided")
    
    success, updated, message = await document_approval_service.update_document(
        document_id=document_id,
        updates=updates,
        updated_by=user["user_id"],
        org_id=document["org_id"]
    )
    
    if not success:
        raise HTTPException(status_code=400, detail=message)
    
    return updated


@router.delete("/{document_id}")
async def delete_document(document_id: str, request: Request):
    """Delete a document"""
    user = await require_auth(request)
    
    document = await document_repository.find_by_id(document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    membership = await get_user_org_membership(user["user_id"], document["org_id"])
    if not membership:
        raise HTTPException(status_code=403, detail="Access denied")
    
    if not has_permission(membership["role"], Permission.DOCUMENT_DELETE):
        raise HTTPException(status_code=403, detail="Permission denied: cannot delete documents")
    
    success, message = await document_approval_service.delete_document(
        document_id=document_id,
        deleted_by=user["user_id"],
        org_id=document["org_id"]
    )
    
    if not success:
        raise HTTPException(status_code=400, detail=message)
    
    return {"message": message}


# ==================== Document Status Change ====================

@router.post("/{document_id}/change-status")
async def change_document_status(
    document_id: str,
    data: DocumentStatusChange,
    request: Request
):
    """
    Change document status.
    If approval is required, this will create an approval request.
    If no approval required, status changes immediately.
    """
    user = await require_auth(request)
    
    document = await document_repository.find_by_id(document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    membership = await get_user_org_membership(user["user_id"], document["org_id"])
    if not membership:
        raise HTTPException(status_code=403, detail="Access denied")
    
    if not has_permission(membership["role"], Permission.DOCUMENT_EDIT):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    if document.get("approval_locked"):
        raise HTTPException(status_code=400, detail="Document is locked pending approval")
    
    current_status = document["status"]
    target_status = data.target_status
    
    if current_status == target_status:
        raise HTTPException(status_code=400, detail="Document is already in this status")
    
    # Check if approval is required
    requires_approval, rule, workflow = await document_approval_service.check_approval_required(
        document_id, current_status, target_status
    )
    
    if requires_approval:
        # Create approval request
        success, approval, message = await document_approval_service.request_approval(
            document_id=document_id,
            target_status=target_status,
            requested_by=user["user_id"],
            org_id=document["org_id"],
            comment=data.comment
        )
        
        if not success:
            raise HTTPException(status_code=400, detail=message)
        
        return {
            "status": "approval_required",
            "message": "Approval request created",
            "approval": approval
        }
    else:
        # Change status directly
        success, updated, message = await document_approval_service.update_document(
            document_id=document_id,
            updates={"status": target_status},
            updated_by=user["user_id"],
            org_id=document["org_id"]
        )
        
        if not success:
            raise HTTPException(status_code=400, detail=message)
        
        return {
            "status": "changed",
            "message": f"Document status changed to {target_status}",
            "document": updated
        }


@router.get("/{document_id}/check-approval")
async def check_document_approval_required(
    document_id: str,
    target_status: str,
    request: Request
):
    """Check if a status change requires approval"""
    user = await require_auth(request)
    
    document = await document_repository.find_by_id(document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    membership = await get_user_org_membership(user["user_id"], document["org_id"])
    if not membership:
        raise HTTPException(status_code=403, detail="Access denied")
    
    requires_approval, rule, workflow = await document_approval_service.check_approval_required(
        document_id, document["status"], target_status
    )
    
    return {
        "requires_approval": requires_approval,
        "current_status": document["status"],
        "target_status": target_status,
        "rule": rule,
        "workflow": {
            "workflow_id": workflow["workflow_id"],
            "name": workflow["name"],
            "scope": workflow.get("scope", "selective")
        } if workflow else None
    }


@router.get("/{document_id}/approval-summary")
async def get_document_approval_summary(document_id: str, request: Request):
    """Get approval summary for a document"""
    user = await require_auth(request)
    
    document = await document_repository.find_by_id(document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    membership = await get_user_org_membership(user["user_id"], document["org_id"])
    if not membership:
        raise HTTPException(status_code=403, detail="Access denied")
    
    summary = await document_approval_service.get_document_approval_summary(
        document_id=document_id,
        user_id=user["user_id"],
        org_id=document["org_id"]
    )
    
    return summary


# ==================== Document Workflow Endpoints ====================

@router.post("/workflows/", response_model=DocumentWorkflowResponse)
async def create_document_workflow(
    data: DocumentWorkflowCreate,
    request: Request,
    org_id: str
):
    """Create a new document workflow"""
    user = await require_auth(request)
    
    membership = await get_user_org_membership(user["user_id"], org_id)
    if not membership:
        raise HTTPException(status_code=403, detail="Access denied")
    
    if not has_permission(membership["role"], Permission.WORKFLOW_CREATE):
        raise HTTPException(status_code=403, detail="Permission denied: cannot create workflows")
    
    success, workflow, message = await document_approval_service.create_workflow(
        org_id=org_id,
        name=data.name,
        description=data.description,
        scope=data.scope.value if hasattr(data.scope, 'value') else data.scope,
        created_by=user["user_id"],
        document_types=[dt.value if hasattr(dt, 'value') else dt for dt in data.document_types],
        project_ids=data.project_ids
    )
    
    if not success:
        raise HTTPException(status_code=400, detail=message)
    
    workflow["rules_count"] = 0
    return workflow


@router.get("/workflows/")
async def get_document_workflows(
    request: Request,
    org_id: str,
    active_only: bool = False,
    include_rules: bool = True
):
    """Get all document workflows for an organization"""
    user = await require_auth(request)
    
    membership = await get_user_org_membership(user["user_id"], org_id)
    if not membership:
        raise HTTPException(status_code=403, detail="Access denied")
    
    if not has_permission(membership["role"], Permission.WORKFLOW_VIEW):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    workflows = await document_workflow_repository.find_workflows_by_org(org_id, active_only)
    
    # Enrich with rule counts and optionally rules
    for wf in workflows:
        if include_rules:
            rules = await document_workflow_repository.find_rules_by_workflow(wf["workflow_id"])
            wf["rules"] = rules
            wf["rules_count"] = len(rules)
        else:
            wf["rules_count"] = await document_workflow_repository.count_rules_by_workflow(wf["workflow_id"])
    
    return workflows


@router.get("/workflows/pending")
async def get_pending_document_approvals(request: Request, org_id: Optional[str] = None):
    """Get pending document approvals for the current user"""
    user = await require_auth(request)
    db = get_database()
    
    if org_id:
        membership = await get_user_org_membership(user["user_id"], org_id)
        if not membership:
            raise HTTPException(status_code=403, detail="Access denied")
        
        approvals = await document_approval_service.get_pending_approvals_for_user(
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
            org_approvals = await document_approval_service.get_pending_approvals_for_user(
                user_id=user["user_id"],
                org_id=mem["org_id"]
            )
            approvals.extend(org_approvals)
    
    # Enrich with document info
    enriched = []
    for approval in approvals:
        document = await document_repository.find_by_id(approval["document_id"])
        requester = await db.users.find_one(
            {"user_id": approval["requested_by"]},
            {"_id": 0, "name": 1}
        )
        
        enriched.append({
            **approval,
            "document_title": document.get("title") if document else "Unknown",
            "project_id": document.get("project_id") if document else None,
            "requester_name": requester.get("name") if requester else "Unknown"
        })
    
    return enriched


@router.get("/workflows/{workflow_id}")
async def get_document_workflow(workflow_id: str, request: Request):
    """Get a document workflow with its rules"""
    user = await require_auth(request)
    
    workflow = await document_workflow_repository.find_workflow_by_id(workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    membership = await get_user_org_membership(user["user_id"], workflow["org_id"])
    if not membership:
        raise HTTPException(status_code=403, detail="Access denied")
    
    if not has_permission(membership["role"], Permission.WORKFLOW_VIEW):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    rules = await document_workflow_repository.find_rules_by_workflow(workflow_id)
    workflow["rules"] = rules
    workflow["rules_count"] = len(rules)
    
    return workflow


@router.put("/workflows/{workflow_id}")
async def update_document_workflow(
    workflow_id: str,
    data: DocumentWorkflowUpdate,
    request: Request
):
    """Update a document workflow"""
    user = await require_auth(request)
    
    workflow = await document_workflow_repository.find_workflow_by_id(workflow_id)
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
            elif isinstance(v, list) and v and hasattr(v[0], 'value'):
                updates[k] = [item.value for item in v]
            else:
                updates[k] = v
    
    if not updates:
        raise HTTPException(status_code=400, detail="No updates provided")
    
    success, updated, message = await document_approval_service.update_workflow(
        workflow_id=workflow_id,
        updates=updates,
        updated_by=user["user_id"],
        org_id=workflow["org_id"]
    )
    
    if not success:
        raise HTTPException(status_code=400, detail=message)
    
    return updated


@router.delete("/workflows/{workflow_id}")
async def delete_document_workflow(workflow_id: str, request: Request):
    """Delete a document workflow"""
    user = await require_auth(request)
    
    workflow = await document_workflow_repository.find_workflow_by_id(workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    membership = await get_user_org_membership(user["user_id"], workflow["org_id"])
    if not membership:
        raise HTTPException(status_code=403, detail="Access denied")
    
    if not has_permission(membership["role"], Permission.WORKFLOW_DELETE):
        raise HTTPException(status_code=403, detail="Permission denied: cannot delete workflows")
    
    success, message = await document_approval_service.delete_workflow(
        workflow_id=workflow_id,
        deleted_by=user["user_id"],
        org_id=workflow["org_id"]
    )
    
    if not success:
        raise HTTPException(status_code=400, detail=message)
    
    return {"message": message}


# ==================== Workflow Rule Endpoints ====================

@router.post("/workflows/{workflow_id}/rules", response_model=DocumentWorkflowRuleResponse)
async def create_document_workflow_rule(
    workflow_id: str,
    data: DocumentWorkflowRuleCreate,
    request: Request
):
    """Create a workflow rule"""
    user = await require_auth(request)
    
    workflow = await document_workflow_repository.find_workflow_by_id(workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    membership = await get_user_org_membership(user["user_id"], workflow["org_id"])
    if not membership:
        raise HTTPException(status_code=403, detail="Access denied")
    
    if not has_permission(membership["role"], Permission.WORKFLOW_EDIT):
        raise HTTPException(status_code=403, detail="Permission denied: cannot create workflow rules")
    
    rule_kwargs = {
        "description": data.description,
        "approval_required": data.approval_required,
        "approval_type": data.approval_type.value if hasattr(data.approval_type, 'value') else data.approval_type,
        "approver_role": data.approver_role.value if hasattr(data.approver_role, 'value') else data.approver_role,
        "specific_approver_ids": data.specific_approver_ids,
        "approval_timeout_minutes": data.approval_timeout_minutes,
        "auto_approve_on_timeout": data.auto_approve_on_timeout,
        "notify_on_request": data.notify_on_request,
        "notify_on_resolution": data.notify_on_resolution,
        "pause_sla": data.pause_sla
    }
    
    success, rule, message = await document_approval_service.create_rule(
        workflow_id=workflow_id,
        from_status=data.from_status,
        to_status=data.to_status,
        created_by=user["user_id"],
        org_id=workflow["org_id"],
        **rule_kwargs
    )
    
    if not success:
        raise HTTPException(status_code=400, detail=message)
    
    return rule


@router.get("/workflows/{workflow_id}/rules")
async def get_document_workflow_rules(workflow_id: str, request: Request):
    """Get all rules for a workflow"""
    user = await require_auth(request)
    
    workflow = await document_workflow_repository.find_workflow_by_id(workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    membership = await get_user_org_membership(user["user_id"], workflow["org_id"])
    if not membership:
        raise HTTPException(status_code=403, detail="Access denied")
    
    if not has_permission(membership["role"], Permission.WORKFLOW_VIEW):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    return await document_workflow_repository.find_rules_by_workflow(workflow_id)


@router.put("/workflows/rules/{rule_id}")
async def update_document_workflow_rule(
    rule_id: str,
    data: DocumentWorkflowRuleUpdate,
    request: Request
):
    """Update a workflow rule"""
    user = await require_auth(request)
    
    rule = await document_workflow_repository.find_rule_by_id(rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    
    workflow = await document_workflow_repository.find_workflow_by_id(rule["workflow_id"])
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
    
    success, updated, message = await document_approval_service.update_rule(
        rule_id=rule_id,
        updates=updates,
        updated_by=user["user_id"],
        org_id=workflow["org_id"]
    )
    
    if not success:
        raise HTTPException(status_code=400, detail=message)
    
    return updated


@router.delete("/workflows/rules/{rule_id}")
async def delete_document_workflow_rule(rule_id: str, request: Request):
    """Delete a workflow rule"""
    user = await require_auth(request)
    
    rule = await document_workflow_repository.find_rule_by_id(rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    
    workflow = await document_workflow_repository.find_workflow_by_id(rule["workflow_id"])
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    membership = await get_user_org_membership(user["user_id"], workflow["org_id"])
    if not membership:
        raise HTTPException(status_code=403, detail="Access denied")
    
    if not has_permission(membership["role"], Permission.WORKFLOW_EDIT):
        raise HTTPException(status_code=403, detail="Permission denied: cannot delete workflow rules")
    
    success, message = await document_approval_service.delete_rule(
        rule_id=rule_id,
        deleted_by=user["user_id"],
        org_id=workflow["org_id"]
    )
    
    if not success:
        raise HTTPException(status_code=400, detail=message)
    
    return {"message": message}


# ==================== Approval Action Endpoints ====================

@router.post("/approvals/{approval_id}/approve")
async def approve_document_request(
    approval_id: str,
    data: DocumentApprovalActionCreate,
    request: Request
):
    """Approve a document approval request"""
    user = await require_auth(request)
    
    approval = await document_workflow_repository.find_approval_by_id(approval_id)
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
    
    success, message = await document_approval_service.approve(
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
async def reject_document_request(
    approval_id: str,
    data: DocumentApprovalActionCreate,
    request: Request
):
    """Reject a document approval request"""
    user = await require_auth(request)
    
    approval = await document_workflow_repository.find_approval_by_id(approval_id)
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
    
    success, message = await document_approval_service.reject(
        approval_id=approval_id,
        acted_by=user["user_id"],
        org_id=approval["org_id"],
        comment=data.comment,
        is_force=is_force
    )
    
    if not success:
        raise HTTPException(status_code=400, detail=message)
    
    return {"message": message}


@router.get("/approvals/{approval_id}")
async def get_document_approval_detail(approval_id: str, request: Request):
    """Get detailed approval info with actions"""
    user = await require_auth(request)
    
    approval = await document_workflow_repository.get_approval_with_actions(approval_id)
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


# ==================== Document Attachments ====================

@router.post("/{document_id}/attachments", response_model=DocumentAttachmentResponse)
async def add_document_attachment(document_id: str, data: DocumentAttachmentCreate, request: Request):
    """Add an attachment to a document"""
    user = await require_auth(request)
    
    document = await document_repository.find_by_id(document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    membership = await get_user_org_membership(user["user_id"], document["org_id"])
    if not membership:
        raise HTTPException(status_code=403, detail="Access denied")
    
    if not has_permission(membership["role"], Permission.DOCUMENT_EDIT):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    attachment = await document_attachment_repository.create({
        "document_id": document_id,
        "filename": data.filename,
        "file_url": data.file_url,
        "file_size": data.file_size,
        "mime_type": data.mime_type,
        "description": data.description,
        "uploaded_by": user["user_id"]
    })
    
    # Enrich with user info
    db = get_database()
    uploader = await db.users.find_one({"user_id": user["user_id"]}, {"_id": 0, "name": 1})
    attachment["uploaded_by_name"] = uploader.get("name") if uploader else "Unknown"
    
    return attachment


@router.get("/{document_id}/attachments")
async def list_document_attachments(document_id: str, request: Request):
    """List all attachments for a document"""
    user = await require_auth(request)
    
    document = await document_repository.find_by_id(document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    membership = await get_user_org_membership(user["user_id"], document["org_id"])
    if not membership:
        raise HTTPException(status_code=403, detail="Access denied")
    
    attachments = await document_attachment_repository.find_by_document(document_id)
    
    # Enrich with user info
    db = get_database()
    enriched = []
    for att in attachments:
        uploader = await db.users.find_one({"user_id": att["uploaded_by"]}, {"_id": 0, "name": 1})
        att["uploaded_by_name"] = uploader.get("name") if uploader else "Unknown"
        enriched.append(att)
    
    return enriched


@router.delete("/attachments/{attachment_id}")
async def delete_document_attachment(attachment_id: str, request: Request):
    """Delete a document attachment"""
    user = await require_auth(request)
    
    attachment = await document_attachment_repository.find_by_id(attachment_id)
    if not attachment:
        raise HTTPException(status_code=404, detail="Attachment not found")
    
    document = await document_repository.find_by_id(attachment["document_id"])
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    membership = await get_user_org_membership(user["user_id"], document["org_id"])
    if not membership:
        raise HTTPException(status_code=403, detail="Access denied")
    
    if not has_permission(membership["role"], Permission.DOCUMENT_EDIT):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    await document_attachment_repository.delete(attachment_id)
    return {"message": "Attachment deleted successfully"}


@router.post("/{document_id}/upload")
async def upload_document_file(document_id: str, request: Request, file: UploadFile = File(...)):
    """Upload a file attachment to a document"""
    user = await require_auth(request)
    
    document = await document_repository.find_by_id(document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    membership = await get_user_org_membership(user["user_id"], document["org_id"])
    if not membership:
        raise HTTPException(status_code=403, detail="Access denied")
    
    if not has_permission(membership["role"], Permission.DOCUMENT_EDIT):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    # Check file size (max 50MB)
    contents = await file.read()
    file_size = len(contents)
    if file_size > 50 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large. Maximum size is 50MB")
    
    # Generate unique filename
    ext = os.path.splitext(file.filename)[1] if file.filename else ""
    unique_filename = f"{uuid.uuid4().hex}{ext}"
    file_path = os.path.join(UPLOAD_DIR, document_id, unique_filename)
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    
    # Save file
    with open(file_path, "wb") as f:
        f.write(contents)
    
    # Create attachment record
    file_url = f"/api/documents/files/{document_id}/{unique_filename}"
    attachment = await document_attachment_repository.create({
        "document_id": document_id,
        "filename": file.filename,
        "file_url": file_url,
        "file_size": file_size,
        "mime_type": file.content_type or "application/octet-stream",
        "uploaded_by": user["user_id"]
    })
    
    # Enrich with user info
    db = get_database()
    uploader = await db.users.find_one({"user_id": user["user_id"]}, {"_id": 0, "name": 1})
    attachment["uploaded_by_name"] = uploader.get("name") if uploader else "Unknown"
    
    return attachment


# ==================== Document Version History ====================

@router.get("/{document_id}/versions")
async def list_document_versions(document_id: str, request: Request, limit: int = 50):
    """List version history for a document"""
    user = await require_auth(request)
    
    document = await document_repository.find_by_id(document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    membership = await get_user_org_membership(user["user_id"], document["org_id"])
    if not membership:
        raise HTTPException(status_code=403, detail="Access denied")
    
    versions = await document_version_repository.find_by_document(document_id, limit)
    
    # Enrich with user info
    db = get_database()
    enriched = []
    for ver in versions:
        changer = await db.users.find_one({"user_id": ver["changed_by"]}, {"_id": 0, "name": 1})
        ver["changed_by_name"] = changer.get("name") if changer else "Unknown"
        enriched.append(ver)
    
    return enriched


@router.get("/versions/{version_id}")
async def get_document_version(version_id: str, request: Request):
    """Get a specific version of a document"""
    user = await require_auth(request)
    
    version = await document_version_repository.find_by_id(version_id)
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")
    
    document = await document_repository.find_by_id(version["document_id"])
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    membership = await get_user_org_membership(user["user_id"], document["org_id"])
    if not membership:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Enrich with user info
    db = get_database()
    changer = await db.users.find_one({"user_id": version["changed_by"]}, {"_id": 0, "name": 1})
    version["changed_by_name"] = changer.get("name") if changer else "Unknown"
    
    return version


@router.post("/{document_id}/versions")
async def create_document_version_snapshot(document_id: str, request: Request, change_summary: str = None):
    """Create a version snapshot of the current document state"""
    user = await require_auth(request)
    
    document = await document_repository.find_by_id(document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    membership = await get_user_org_membership(user["user_id"], document["org_id"])
    if not membership:
        raise HTTPException(status_code=403, detail="Access denied")
    
    if not has_permission(membership["role"], Permission.DOCUMENT_EDIT):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    # Get latest version number
    latest = await document_version_repository.find_latest(document_id)
    next_version = (latest["version_number"] + 1) if latest else 1
    
    # Create version snapshot
    version = await document_version_repository.create({
        "document_id": document_id,
        "version_number": next_version,
        "title": document["title"],
        "description": document.get("description"),
        "content": document.get("content"),
        "status": document["status"],
        "changed_by": user["user_id"],
        "change_summary": change_summary
    })
    
    # Update document version number
    await document_repository.update(document_id, {"version": next_version})
    
    # Enrich with user info
    db = get_database()
    changer = await db.users.find_one({"user_id": user["user_id"]}, {"_id": 0, "name": 1})
    version["changed_by_name"] = changer.get("name") if changer else "Unknown"
    
    return version
