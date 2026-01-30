"""Budget Approval Models"""
from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


class BudgetApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class BudgetChangeType(str, Enum):
    AMOUNT_INCREASE = "amount_increase"
    AMOUNT_DECREASE = "amount_decrease"
    THRESHOLD_CHANGE = "threshold_change"
    HARD_LIMIT_CHANGE = "hard_limit_change"
    OTHER = "other"


class BudgetApprovalCreate(BaseModel):
    budget_id: str
    change_type: BudgetChangeType
    current_value: float
    proposed_value: float
    reason: Optional[str] = None


class BudgetApprovalResponse(BaseModel):
    approval_id: str
    budget_id: str
    project_id: str
    project_name: str
    change_type: BudgetChangeType
    current_value: float
    proposed_value: float
    reason: Optional[str] = None
    status: BudgetApprovalStatus
    requested_by: str
    requester_name: str
    created_at: str
    reviewed_by: Optional[str] = None
    reviewer_name: Optional[str] = None
    reviewed_at: Optional[str] = None
    review_notes: Optional[str] = None


class BudgetApprovalDecision(BaseModel):
    notes: Optional[str] = None
