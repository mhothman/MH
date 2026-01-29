"""Task-related models"""
from pydantic import BaseModel, ConfigDict, field_validator, model_validator
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime
from enum import Enum


class TaskStatus(str, Enum):
    """Valid task statuses"""
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    IN_REVIEW = "in_review"
    DONE = "done"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"


class TaskPriority(str, Enum):
    """Valid task priorities"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


# Allow string literals for backward compatibility
VALID_STATUSES = {s.value for s in TaskStatus}
VALID_PRIORITIES = {p.value for p in TaskPriority}


class SubtaskCreate(BaseModel):
    title: str
    completed: bool = False
    
    @field_validator('title')
    @classmethod
    def title_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError('Subtask title cannot be empty')
        return v.strip()


class SubtaskUpdate(BaseModel):
    title: Optional[str] = None
    completed: Optional[bool] = None
    
    @field_validator('title')
    @classmethod
    def title_not_empty(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not v.strip():
            raise ValueError('Subtask title cannot be empty')
        return v.strip() if v else v


class TaskCreate(BaseModel):
    project_id: str  # Required - the project this task belongs to
    title: str
    description: Optional[str] = None
    status: str = "todo"
    priority: str = "medium"
    due_date: Optional[str] = None
    start_date: Optional[str] = None
    assignee_ids: List[str] = []
    dependencies: List[str] = []
    subtasks: List[SubtaskCreate] = []
    estimated_hours: Optional[float] = None
    recurring_rule: Optional[Dict[str, Any]] = None
    baseline_start: Optional[str] = None
    baseline_end: Optional[str] = None
    
    @field_validator('title')
    @classmethod
    def title_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError('Task title cannot be empty')
        if len(v.strip()) > 500:
            raise ValueError('Task title cannot exceed 500 characters')
        return v.strip()
    
    @field_validator('status')
    @classmethod
    def validate_status(cls, v: str) -> str:
        if v not in VALID_STATUSES:
            raise ValueError(f'Invalid status. Must be one of: {", ".join(VALID_STATUSES)}')
        return v
    
    @field_validator('priority')
    @classmethod
    def validate_priority(cls, v: str) -> str:
        if v not in VALID_PRIORITIES:
            raise ValueError(f'Invalid priority. Must be one of: {", ".join(VALID_PRIORITIES)}')
        return v
    
    @field_validator('estimated_hours')
    @classmethod
    def validate_estimated_hours(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and v < 0:
            raise ValueError('Estimated hours cannot be negative')
        return v


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    due_date: Optional[str] = None
    start_date: Optional[str] = None
    assignee_ids: Optional[List[str]] = None
    dependencies: Optional[List[str]] = None
    subtasks: Optional[List[Dict[str, Any]]] = None
    estimated_hours: Optional[float] = None
    recurring_rule: Optional[Dict[str, Any]] = None
    baseline_start: Optional[str] = None
    baseline_end: Optional[str] = None
    
    @field_validator('title')
    @classmethod
    def title_not_empty(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            if not v.strip():
                raise ValueError('Task title cannot be empty')
            if len(v.strip()) > 500:
                raise ValueError('Task title cannot exceed 500 characters')
            return v.strip()
        return v
    
    @field_validator('status')
    @classmethod
    def validate_status(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in VALID_STATUSES:
            raise ValueError(f'Invalid status. Must be one of: {", ".join(VALID_STATUSES)}')
        return v
    
    @field_validator('priority')
    @classmethod
    def validate_priority(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in VALID_PRIORITIES:
            raise ValueError(f'Invalid priority. Must be one of: {", ".join(VALID_PRIORITIES)}')
        return v
    
    @field_validator('estimated_hours')
    @classmethod
    def validate_estimated_hours(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and v < 0:
            raise ValueError('Estimated hours cannot be negative')
        return v

class TaskResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    task_id: str
    project_id: str
    title: str
    description: Optional[str] = None
    status: str
    priority: str
    due_date: Optional[str] = None
    start_date: Optional[str] = None
    assignee_ids: List[str] = []
    dependencies: List[str] = []
    subtasks: List[Dict[str, Any]] = []
    estimated_hours: Optional[float] = None
    actual_hours: float = 0
    recurring_rule: Optional[Dict[str, Any]] = None
    baseline_start: Optional[str] = None
    baseline_end: Optional[str] = None
    created_by: str
    created_at: datetime
    updated_at: datetime
