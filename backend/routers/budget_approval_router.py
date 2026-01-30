"""Budget Approval Router - API endpoints for budget approval workflow"""
from fastapi import APIRouter, HTTPException, Request
from typing import List
import logging

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.security import require_auth, require_permission
from core.permissions import Permission
from models.budget_approval import (
    BudgetApprovalCreate,
    BudgetApprovalResponse,
    BudgetApprovalDecision
)
from services.budget_approval_service import budget_approval_service

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/request", response_model=BudgetApprovalResponse)
async def request_budget_change(data: BudgetApprovalCreate, request: Request, org_id: str):
    """Request approval for a budget change"""
    user = await require_auth(request)
    
    try:
        approval = await budget_approval_service.create_approval_request(
            budget_id=data.budget_id,
            change_type=data.change_type,
            current_value=data.current_value,
            proposed_value=data.proposed_value,
            reason=data.reason,
            requested_by=user["user_id"],
            org_id=org_id
        )
        return BudgetApprovalResponse(**approval)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{approval_id}/approve", response_model=BudgetApprovalResponse)
async def approve_budget_change(approval_id: str, decision: BudgetApprovalDecision, request: Request, org_id: str):
    """Approve a budget change request (Finance role only)"""
    user = await require_permission(request, org_id, Permission.BUDGET_APPROVE)
    
    success, message, approval = await budget_approval_service.approve_request(
        approval_id=approval_id,
        reviewed_by=user["user_id"],
        notes=decision.notes
    )
    
    if not success:
        raise HTTPException(status_code=400, detail=message)
    
    return BudgetApprovalResponse(**approval)


@router.post("/{approval_id}/reject", response_model=BudgetApprovalResponse)
async def reject_budget_change(approval_id: str, decision: BudgetApprovalDecision, request: Request, org_id: str):
    """Reject a budget change request (Finance role only)"""
    user = await require_permission(request, org_id, Permission.BUDGET_APPROVE)
    
    success, message, approval = await budget_approval_service.reject_request(
        approval_id=approval_id,
        reviewed_by=user["user_id"],
        notes=decision.notes
    )
    
    if not success:
        raise HTTPException(status_code=400, detail=message)
    
    return BudgetApprovalResponse(**approval)


@router.get("/pending/org/{org_id}", response_model=List[BudgetApprovalResponse])
async def get_pending_approvals(org_id: str, request: Request):
    """Get all pending budget approval requests for an organization (Finance role only)"""
    await require_permission(request, org_id, Permission.BUDGET_APPROVE)
    
    approvals = await budget_approval_service.get_pending_approvals(org_id)
    return [BudgetApprovalResponse(**a) for a in approvals]


@router.get("/{approval_id}", response_model=BudgetApprovalResponse)
async def get_approval(approval_id: str, request: Request):
    """Get a specific budget approval request"""
    user = await require_auth(request)
    
    approval = await budget_approval_service.get_approval(approval_id)
    if not approval:
        raise HTTPException(status_code=404, detail="Approval request not found")
    
    return BudgetApprovalResponse(**approval)


@router.get("/budget/{budget_id}", response_model=List[BudgetApprovalResponse])
async def get_budget_approval_history(budget_id: str, request: Request):
    """Get all approval requests for a specific budget"""
    user = await require_auth(request)
    
    approvals = await budget_approval_service.get_budget_approvals(budget_id)
    return [BudgetApprovalResponse(**a) for a in approvals]
