"""Budget Management Router for Project Budget Management"""
from fastapi import APIRouter, HTTPException, Request, Query
from datetime import datetime, timezone
from typing import Optional, List
import logging

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.database import get_database
from core.security import require_auth, require_permission, get_user_org_membership
from core.permissions import Permission
from models.budget import (
    ProjectBudgetCreate,
    ProjectBudgetUpdate,
    ProjectBudgetResponse,
    BudgetTransactionCreate,
    BudgetTransactionResponse,
    BudgetRevisionResponse,
    ExpenseCreate,
    ExpenseUpdate,
    ExpenseResponse,
    BillableRateCreate,
    BillableRateResponse,
    BudgetSummaryResponse,
    EXPENSE_CATEGORIES,
)
from services.budget_service import budget_service

logger = logging.getLogger(__name__)
router = APIRouter()


# ==================== Budget Endpoints ====================

@router.post("/", response_model=ProjectBudgetResponse)
async def create_budget(data: ProjectBudgetCreate, request: Request, org_id: str):
    """Create a new project budget"""
    user = await require_permission(request, org_id, Permission.BUDGET_CREATE)
    
    try:
        budget = await budget_service.create_budget(
            org_id=org_id,
            project_id=data.project_id,
            total_budget=data.total_budget,
            currency=data.currency,
            warning_threshold_percent=data.warning_threshold_percent,
            hard_limit=data.hard_limit,
            notes=data.notes,
            created_by=user["user_id"]
        )
        return ProjectBudgetResponse(**budget)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/project/{project_id}", response_model=ProjectBudgetResponse)
async def get_project_budget(project_id: str, request: Request):
    """Get budget for a specific project"""
    user = await require_auth(request)
    
    budget = await budget_service.get_budget_by_project(project_id)
    if not budget:
        raise HTTPException(status_code=404, detail="Budget not found for this project")
    
    # Verify user has access to this org
    membership = await get_user_org_membership(user["user_id"], budget["org_id"])
    if not membership:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return ProjectBudgetResponse(**budget)


@router.get("/org/{org_id}", response_model=List[ProjectBudgetResponse])
async def get_org_budgets(org_id: str, request: Request):
    """Get all budgets for an organization"""
    await require_permission(request, org_id, Permission.BUDGET_VIEW)
    
    budgets = await budget_service.get_budgets_by_org(org_id)
    return [ProjectBudgetResponse(**b) for b in budgets]


@router.get("/{budget_id}", response_model=ProjectBudgetResponse)
async def get_budget(budget_id: str, request: Request):
    """Get budget by ID"""
    user = await require_auth(request)
    
    budget = await budget_service.get_budget(budget_id)
    if not budget:
        raise HTTPException(status_code=404, detail="Budget not found")
    
    # Verify user has access
    membership = await get_user_org_membership(user["user_id"], budget["org_id"])
    if not membership:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return ProjectBudgetResponse(**budget)


@router.put("/{budget_id}", response_model=ProjectBudgetResponse)
async def update_budget(
    budget_id: str,
    data: ProjectBudgetUpdate,
    request: Request,
    reason: Optional[str] = Query(None, description="Reason for budget change")
):
    """Update a project budget"""
    user = await require_auth(request)
    
    budget = await budget_service.get_budget(budget_id)
    if not budget:
        raise HTTPException(status_code=404, detail="Budget not found")
    
    await require_permission(request, budget["org_id"], Permission.BUDGET_EDIT)
    
    try:
        updates = data.model_dump(exclude_unset=True)
        updated_budget = await budget_service.update_budget(
            budget_id=budget_id,
            updates=updates,
            updated_by=user["user_id"],
            reason=reason
        )
        return ProjectBudgetResponse(**updated_budget)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{budget_id}")
async def delete_budget(budget_id: str, request: Request):
    """Delete a project budget"""
    user = await require_auth(request)
    
    budget = await budget_service.get_budget(budget_id)
    if not budget:
        raise HTTPException(status_code=404, detail="Budget not found")
    
    await require_permission(request, budget["org_id"], Permission.BUDGET_DELETE)
    
    await budget_service.delete_budget(budget_id, user["user_id"])
    return {"message": "Budget deleted successfully"}


@router.get("/{budget_id}/summary", response_model=BudgetSummaryResponse)
async def get_budget_summary(budget_id: str, request: Request):
    """Get comprehensive budget summary with breakdown"""
    user = await require_auth(request)
    
    budget = await budget_service.get_budget(budget_id)
    if not budget:
        raise HTTPException(status_code=404, detail="Budget not found")
    
    membership = await get_user_org_membership(user["user_id"], budget["org_id"])
    if not membership:
        raise HTTPException(status_code=403, detail="Access denied")
    
    try:
        summary = await budget_service.get_budget_summary(budget_id)
        return BudgetSummaryResponse(**summary)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{budget_id}/override-lock")
async def override_budget_lock(budget_id: str, request: Request):
    """Override budget lock (admin action)"""
    user = await require_auth(request)
    
    budget = await budget_service.get_budget(budget_id)
    if not budget:
        raise HTTPException(status_code=404, detail="Budget not found")
    
    await require_permission(request, budget["org_id"], Permission.BUDGET_OVERRIDE)
    
    try:
        updated = await budget_service.override_lock(budget_id, user["user_id"])
        return ProjectBudgetResponse(**updated)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ==================== Transaction Endpoints ====================

@router.post("/{budget_id}/transactions", response_model=BudgetTransactionResponse)
async def create_transaction(
    budget_id: str,
    data: BudgetTransactionCreate,
    request: Request
):
    """Create a manual budget transaction"""
    user = await require_auth(request)
    
    budget = await budget_service.get_budget(budget_id)
    if not budget:
        raise HTTPException(status_code=404, detail="Budget not found")
    
    await require_permission(request, budget["org_id"], Permission.BUDGET_EDIT)
    
    try:
        transaction = await budget_service.create_transaction(
            budget_id=budget_id,
            source=data.source,
            amount=data.amount,
            created_by=user["user_id"],
            reference_id=data.reference_id,
            description=data.description
        )
        return BudgetTransactionResponse(**transaction)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{budget_id}/transactions", response_model=List[BudgetTransactionResponse])
async def get_transactions(
    budget_id: str,
    request: Request,
    source: Optional[str] = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0)
):
    """Get transactions for a budget"""
    user = await require_auth(request)
    
    budget = await budget_service.get_budget(budget_id)
    if not budget:
        raise HTTPException(status_code=404, detail="Budget not found")
    
    membership = await get_user_org_membership(user["user_id"], budget["org_id"])
    if not membership:
        raise HTTPException(status_code=403, detail="Access denied")
    
    transactions = await budget_service.get_transactions(
        budget_id=budget_id,
        source=source,
        limit=limit,
        offset=offset
    )
    return [BudgetTransactionResponse(**t) for t in transactions]


@router.delete("/transactions/{transaction_id}")
async def delete_transaction(transaction_id: str, request: Request):
    """Delete a budget transaction"""
    user = await require_auth(request)
    db = get_database()
    
    transaction = await db.budget_transactions.find_one(
        {"transaction_id": transaction_id},
        {"_id": 0}
    )
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    budget = await budget_service.get_budget(transaction["budget_id"])
    await require_permission(request, budget["org_id"], Permission.BUDGET_EDIT)
    
    await budget_service.delete_transaction(transaction_id, user["user_id"])
    return {"message": "Transaction deleted successfully"}


# ==================== Revision History Endpoints ====================

@router.get("/{budget_id}/revisions", response_model=List[BudgetRevisionResponse])
async def get_revisions(budget_id: str, request: Request):
    """Get budget revision history"""
    user = await require_auth(request)
    
    budget = await budget_service.get_budget(budget_id)
    if not budget:
        raise HTTPException(status_code=404, detail="Budget not found")
    
    membership = await get_user_org_membership(user["user_id"], budget["org_id"])
    if not membership:
        raise HTTPException(status_code=403, detail="Access denied")
    
    revisions = await budget_service.get_revisions(budget_id)
    return [BudgetRevisionResponse(**r) for r in revisions]


# ==================== Expense Endpoints ====================

@router.post("/expenses/", response_model=ExpenseResponse)
async def create_expense(data: ExpenseCreate, request: Request, org_id: str):
    """Create a new expense entry"""
    user = await require_permission(request, org_id, Permission.EXPENSE_CREATE)
    
    try:
        expense = await budget_service.create_expense(
            org_id=org_id,
            project_id=data.project_id,
            title=data.title,
            amount=data.amount,
            currency=data.currency,
            category=data.category,
            date=data.date,
            created_by=user["user_id"],
            description=data.description,
            document_id=data.document_id
        )
        return ExpenseResponse(**expense)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/expenses/project/{project_id}", response_model=List[ExpenseResponse])
async def get_project_expenses(
    project_id: str,
    request: Request,
    category: Optional[str] = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0)
):
    """Get expenses for a project"""
    user = await require_auth(request)
    db = get_database()
    
    # Get project to verify access
    project = await db.projects.find_one({"project_id": project_id}, {"_id": 0, "org_id": 1})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    membership = await get_user_org_membership(user["user_id"], project["org_id"])
    if not membership:
        raise HTTPException(status_code=403, detail="Access denied")
    
    expenses = await budget_service.get_expenses_by_project(
        project_id=project_id,
        category=category,
        limit=limit,
        offset=offset
    )
    return [ExpenseResponse(**e) for e in expenses]


@router.get("/expenses/{expense_id}", response_model=ExpenseResponse)
async def get_expense(expense_id: str, request: Request):
    """Get expense by ID"""
    user = await require_auth(request)
    
    expense = await budget_service.get_expense(expense_id)
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    
    membership = await get_user_org_membership(user["user_id"], expense["org_id"])
    if not membership:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return ExpenseResponse(**expense)


@router.put("/expenses/{expense_id}", response_model=ExpenseResponse)
async def update_expense(expense_id: str, data: ExpenseUpdate, request: Request):
    """Update an expense"""
    user = await require_auth(request)
    
    expense = await budget_service.get_expense(expense_id)
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    
    await require_permission(request, expense["org_id"], Permission.EXPENSE_EDIT)
    
    try:
        updates = data.model_dump(exclude_unset=True)
        updated = await budget_service.update_expense(
            expense_id=expense_id,
            updates=updates,
            updated_by=user["user_id"]
        )
        return ExpenseResponse(**updated)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/expenses/{expense_id}")
async def delete_expense(expense_id: str, request: Request):
    """Delete an expense"""
    user = await require_auth(request)
    
    expense = await budget_service.get_expense(expense_id)
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    
    await require_permission(request, expense["org_id"], Permission.EXPENSE_DELETE)
    
    await budget_service.delete_expense(expense_id, user["user_id"])
    return {"message": "Expense deleted successfully"}


@router.get("/expenses/categories/list")
async def get_expense_categories():
    """Get list of expense categories"""
    return EXPENSE_CATEGORIES


# ==================== Billable Rate Endpoints ====================

@router.post("/rates/", response_model=BillableRateResponse)
async def set_billable_rate(data: BillableRateCreate, request: Request, org_id: str):
    """Set billable rate for user/project/org"""
    user = await require_permission(request, org_id, Permission.BUDGET_EDIT)
    
    try:
        rate = await budget_service.set_billable_rate(
            org_id=org_id,
            hourly_rate=data.hourly_rate,
            currency=data.currency,
            created_by=user["user_id"],
            user_id=data.user_id,
            project_id=data.project_id,
            effective_from=data.effective_from
        )
        return BillableRateResponse(**rate)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/rates/org/{org_id}", response_model=List[BillableRateResponse])
async def get_org_rates(org_id: str, request: Request):
    """Get all billable rates for an organization"""
    await require_permission(request, org_id, Permission.BUDGET_VIEW)
    
    rates = await budget_service.get_billable_rates(org_id)
    return [BillableRateResponse(**r) for r in rates]


@router.get("/rates/effective")
async def get_effective_rate(
    request: Request,
    org_id: str,
    user_id: Optional[str] = None,
    project_id: Optional[str] = None
):
    """Get effective billable rate for a specific user/project combination"""
    await require_permission(request, org_id, Permission.BUDGET_VIEW)
    
    rate = await budget_service.get_billable_rate(org_id, user_id, project_id)
    return {"hourly_rate": rate, "user_id": user_id, "project_id": project_id}


# ==================== Budget Lock Check ====================

@router.get("/check-lock/{project_id}")
async def check_budget_lock(project_id: str, request: Request):
    """Check if project budget is locked"""
    user = await require_auth(request)
    db = get_database()
    
    project = await db.projects.find_one({"project_id": project_id}, {"_id": 0, "org_id": 1})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    membership = await get_user_org_membership(user["user_id"], project["org_id"])
    if not membership:
        raise HTTPException(status_code=403, detail="Access denied")
    
    lock_status = await budget_service.check_budget_lock(project_id)
    return lock_status
