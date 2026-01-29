"""Budget-related models for Project Budget Management"""
from pydantic import BaseModel, ConfigDict, field_validator, model_validator, Field
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime
from enum import Enum


class Currency(str, Enum):
    """Supported currencies"""
    USD = "USD"
    EGP = "EGP"


class BudgetStatus(str, Enum):
    """Budget status values"""
    ACTIVE = "active"
    WARNING = "warning"  # Threshold exceeded
    EXCEEDED = "exceeded"  # 100% exceeded
    LOCKED = "locked"  # Hard limit triggered


class TransactionSource(str, Enum):
    """Source of budget transaction"""
    TIME_ENTRY = "time_entry"
    EXPENSE = "expense"
    MANUAL = "manual"
    ADJUSTMENT = "adjustment"


VALID_CURRENCIES = {c.value for c in Currency}
VALID_STATUSES = {s.value for s in BudgetStatus}
VALID_SOURCES = {s.value for s in TransactionSource}


# ==================== Project Budget Models ====================

class ProjectBudgetCreate(BaseModel):
    """Model for creating a project budget"""
    project_id: str
    total_budget: float = Field(..., gt=0, description="Total budget amount")
    currency: str = "EGP"
    warning_threshold_percent: float = Field(default=80.0, ge=0, le=100)
    hard_limit: bool = False  # If true, block operations when exceeded
    notes: Optional[str] = None
    
    @field_validator('project_id')
    @classmethod
    def project_id_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError('Project ID is required')
        return v.strip()
    
    @field_validator('total_budget')
    @classmethod
    def validate_budget(cls, v: float) -> float:
        if v <= 0:
            raise ValueError('Budget must be positive')
        if v > 999999999999:  # 1 trillion limit
            raise ValueError('Budget exceeds maximum allowed value')
        return round(v, 2)
    
    @field_validator('currency')
    @classmethod
    def validate_currency(cls, v: str) -> str:
        if v.upper() not in VALID_CURRENCIES:
            raise ValueError(f'Invalid currency. Must be one of: {", ".join(VALID_CURRENCIES)}')
        return v.upper()
    
    @field_validator('warning_threshold_percent')
    @classmethod
    def validate_threshold(cls, v: float) -> float:
        if v < 0 or v > 100:
            raise ValueError('Warning threshold must be between 0 and 100')
        return round(v, 1)
    
    @field_validator('notes')
    @classmethod
    def validate_notes(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and len(v) > 2000:
            raise ValueError('Notes cannot exceed 2000 characters')
        return v


class ProjectBudgetUpdate(BaseModel):
    """Model for updating a project budget"""
    total_budget: Optional[float] = None
    currency: Optional[str] = None
    warning_threshold_percent: Optional[float] = None
    hard_limit: Optional[bool] = None
    notes: Optional[str] = None
    
    @field_validator('total_budget')
    @classmethod
    def validate_budget(cls, v: Optional[float]) -> Optional[float]:
        if v is not None:
            if v <= 0:
                raise ValueError('Budget must be positive')
            if v > 999999999999:
                raise ValueError('Budget exceeds maximum allowed value')
            return round(v, 2)
        return v
    
    @field_validator('currency')
    @classmethod
    def validate_currency(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v.upper() not in VALID_CURRENCIES:
            raise ValueError(f'Invalid currency. Must be one of: {", ".join(VALID_CURRENCIES)}')
        return v.upper() if v else v
    
    @field_validator('warning_threshold_percent')
    @classmethod
    def validate_threshold(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and (v < 0 or v > 100):
            raise ValueError('Warning threshold must be between 0 and 100')
        return round(v, 1) if v is not None else v
    
    @field_validator('notes')
    @classmethod
    def validate_notes(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and len(v) > 2000:
            raise ValueError('Notes cannot exceed 2000 characters')
        return v


class ProjectBudgetResponse(BaseModel):
    """Response model for project budget"""
    model_config = ConfigDict(from_attributes=True)
    
    budget_id: str
    org_id: str
    project_id: str
    total_budget: float
    currency: str
    warning_threshold_percent: float
    hard_limit: bool
    status: str
    spent_amount: float
    remaining_amount: float
    spent_percent: float
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    created_by: str


# ==================== Budget Transaction Models ====================

class BudgetTransactionCreate(BaseModel):
    """Model for creating a budget transaction"""
    source: str = "manual"
    reference_id: Optional[str] = None  # ID of related entity (task, expense, etc.)
    amount: float = Field(..., description="Transaction amount (positive for expense, negative for credit)")
    description: Optional[str] = None
    
    @field_validator('source')
    @classmethod
    def validate_source(cls, v: str) -> str:
        if v not in VALID_SOURCES:
            raise ValueError(f'Invalid source. Must be one of: {", ".join(VALID_SOURCES)}')
        return v
    
    @field_validator('amount')
    @classmethod
    def validate_amount(cls, v: float) -> float:
        if v == 0:
            raise ValueError('Amount cannot be zero')
        if abs(v) > 999999999999:
            raise ValueError('Amount exceeds maximum allowed value')
        return round(v, 2)
    
    @field_validator('description')
    @classmethod
    def validate_description(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and len(v) > 500:
            raise ValueError('Description cannot exceed 500 characters')
        return v


class BudgetTransactionResponse(BaseModel):
    """Response model for budget transaction"""
    model_config = ConfigDict(from_attributes=True)
    
    transaction_id: str
    budget_id: str
    source: str
    reference_id: Optional[str] = None
    amount: float
    description: Optional[str] = None
    created_at: datetime
    created_by: str
    created_by_name: Optional[str] = None


# ==================== Budget Revision Models ====================

class BudgetRevisionResponse(BaseModel):
    """Response model for budget revision history"""
    model_config = ConfigDict(from_attributes=True)
    
    revision_id: str
    budget_id: str
    previous_budget: float
    new_budget: float
    change_amount: float
    reason: Optional[str] = None
    approved_by: Optional[str] = None
    created_at: datetime
    created_by: str
    created_by_name: Optional[str] = None


# ==================== Expense Models ====================

class ExpenseCreate(BaseModel):
    """Model for creating an expense entry"""
    project_id: str
    title: str = Field(..., min_length=1, max_length=200)
    amount: float = Field(..., gt=0)
    currency: str = "EGP"
    category: str = "general"
    date: str  # YYYY-MM-DD
    description: Optional[str] = None
    document_id: Optional[str] = None  # Link to document (receipt, invoice)
    
    @field_validator('project_id')
    @classmethod
    def project_id_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError('Project ID is required')
        return v.strip()
    
    @field_validator('title')
    @classmethod
    def title_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError('Expense title is required')
        return v.strip()
    
    @field_validator('amount')
    @classmethod
    def validate_amount(cls, v: float) -> float:
        if v <= 0:
            raise ValueError('Amount must be positive')
        if v > 999999999999:
            raise ValueError('Amount exceeds maximum allowed value')
        return round(v, 2)
    
    @field_validator('currency')
    @classmethod
    def validate_currency(cls, v: str) -> str:
        if v.upper() not in VALID_CURRENCIES:
            raise ValueError(f'Invalid currency. Must be one of: {", ".join(VALID_CURRENCIES)}')
        return v.upper()
    
    @field_validator('category')
    @classmethod
    def validate_category(cls, v: str) -> str:
        valid_categories = {'general', 'travel', 'equipment', 'software', 'services', 'materials', 'other'}
        if v.lower() not in valid_categories:
            raise ValueError(f'Invalid category. Must be one of: {", ".join(valid_categories)}')
        return v.lower()
    
    @field_validator('date')
    @classmethod
    def validate_date(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError('Date is required')
        try:
            datetime.strptime(v, '%Y-%m-%d')
        except ValueError:
            raise ValueError('Invalid date format. Must be YYYY-MM-DD')
        return v
    
    @field_validator('description')
    @classmethod
    def validate_description(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and len(v) > 1000:
            raise ValueError('Description cannot exceed 1000 characters')
        return v


class ExpenseUpdate(BaseModel):
    """Model for updating an expense"""
    title: Optional[str] = None
    amount: Optional[float] = None
    currency: Optional[str] = None
    category: Optional[str] = None
    date: Optional[str] = None
    description: Optional[str] = None
    document_id: Optional[str] = None
    
    @field_validator('title')
    @classmethod
    def title_not_empty(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not v.strip():
            raise ValueError('Expense title cannot be empty')
        return v.strip() if v else v
    
    @field_validator('amount')
    @classmethod
    def validate_amount(cls, v: Optional[float]) -> Optional[float]:
        if v is not None:
            if v <= 0:
                raise ValueError('Amount must be positive')
            if v > 999999999999:
                raise ValueError('Amount exceeds maximum allowed value')
            return round(v, 2)
        return v
    
    @field_validator('currency')
    @classmethod
    def validate_currency(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v.upper() not in VALID_CURRENCIES:
            raise ValueError(f'Invalid currency. Must be one of: {", ".join(VALID_CURRENCIES)}')
        return v.upper() if v else v


class ExpenseResponse(BaseModel):
    """Response model for expense"""
    model_config = ConfigDict(from_attributes=True)
    
    expense_id: str
    org_id: str
    project_id: str
    title: str
    amount: float
    currency: str
    category: str
    date: str
    description: Optional[str] = None
    document_id: Optional[str] = None
    document_title: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    created_by: str
    created_by_name: Optional[str] = None


# ==================== Billable Rate Models ====================

class BillableRateCreate(BaseModel):
    """Model for creating/updating billable rate"""
    user_id: Optional[str] = None  # If null, applies to org default
    project_id: Optional[str] = None  # If null, applies to all projects
    hourly_rate: float = Field(..., ge=0)
    currency: str = "EGP"
    effective_from: Optional[str] = None  # YYYY-MM-DD
    
    @field_validator('hourly_rate')
    @classmethod
    def validate_rate(cls, v: float) -> float:
        if v < 0:
            raise ValueError('Hourly rate cannot be negative')
        if v > 99999:
            raise ValueError('Hourly rate exceeds maximum allowed value')
        return round(v, 2)
    
    @field_validator('currency')
    @classmethod
    def validate_currency(cls, v: str) -> str:
        if v.upper() not in VALID_CURRENCIES:
            raise ValueError(f'Invalid currency. Must be one of: {", ".join(VALID_CURRENCIES)}')
        return v.upper()


class BillableRateResponse(BaseModel):
    """Response model for billable rate"""
    model_config = ConfigDict(from_attributes=True)
    
    rate_id: str
    org_id: str
    user_id: Optional[str] = None
    user_name: Optional[str] = None
    project_id: Optional[str] = None
    project_name: Optional[str] = None
    hourly_rate: float
    currency: str
    effective_from: Optional[str] = None
    created_at: datetime
    updated_at: datetime


# ==================== Budget Summary Models ====================

class BudgetSummaryResponse(BaseModel):
    """Comprehensive budget summary with breakdown"""
    model_config = ConfigDict(from_attributes=True)
    
    budget_id: str
    project_id: str
    project_name: str
    total_budget: float
    currency: str
    status: str
    warning_threshold_percent: float
    hard_limit: bool
    
    # Spend breakdown
    total_spent: float
    time_cost: float
    expense_cost: float
    manual_adjustments: float
    
    # Calculated fields
    remaining: float
    spent_percent: float
    burn_rate_daily: Optional[float] = None  # Average daily spend
    projected_end_date: Optional[str] = None  # When budget will run out at current rate
    days_remaining: Optional[int] = None
    
    # Alerts
    is_warning: bool
    is_exceeded: bool
    is_locked: bool


# ==================== Expense Categories ====================

EXPENSE_CATEGORIES = [
    {"id": "general", "label": "General", "icon": "receipt"},
    {"id": "travel", "label": "Travel", "icon": "plane"},
    {"id": "equipment", "label": "Equipment", "icon": "monitor"},
    {"id": "software", "label": "Software", "icon": "code"},
    {"id": "services", "label": "Services", "icon": "users"},
    {"id": "materials", "label": "Materials", "icon": "package"},
    {"id": "other", "label": "Other", "icon": "more-horizontal"},
]
