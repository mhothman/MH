"""Project-related models"""
from pydantic import BaseModel, ConfigDict, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
import re


class ProjectStatus(str, Enum):
    """Valid project statuses"""
    PLANNED = "planned"
    ACTIVE = "active"
    ON_HOLD = "on_hold"
    COMPLETED = "completed"
    ARCHIVED = "archived"
    CANCELLED = "cancelled"


VALID_PROJECT_STATUSES = {s.value for s in ProjectStatus}

# Regex for valid hex color
HEX_COLOR_PATTERN = re.compile(r'^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$')


class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None
    status: str = "planned"
    color: str = "#3B82F6"
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    customer_id: Optional[str] = None
    task_statuses: Optional[List[Dict[str, Any]]] = None
    
    @field_validator('name')
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError('Project name cannot be empty')
        if len(v.strip()) > 200:
            raise ValueError('Project name cannot exceed 200 characters')
        return v.strip()
    
    @field_validator('description')
    @classmethod
    def validate_description(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and len(v) > 5000:
            raise ValueError('Project description cannot exceed 5000 characters')
        return v
    
    @field_validator('status')
    @classmethod
    def validate_status(cls, v: str) -> str:
        if v not in VALID_PROJECT_STATUSES:
            raise ValueError(f'Invalid status. Must be one of: {", ".join(VALID_PROJECT_STATUSES)}')
        return v
    
    @field_validator('color')
    @classmethod
    def validate_color(cls, v: str) -> str:
        if not HEX_COLOR_PATTERN.match(v):
            raise ValueError('Invalid color format. Must be a valid hex color (e.g., #3B82F6)')
        return v.upper()


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    color: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    customer_id: Optional[str] = None
    task_statuses: Optional[List[Dict[str, Any]]] = None
    
    @field_validator('name')
    @classmethod
    def name_not_empty(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            if not v.strip():
                raise ValueError('Project name cannot be empty')
            if len(v.strip()) > 200:
                raise ValueError('Project name cannot exceed 200 characters')
            return v.strip()
        return v
    
    @field_validator('description')
    @classmethod
    def validate_description(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and len(v) > 5000:
            raise ValueError('Project description cannot exceed 5000 characters')
        return v
    
    @field_validator('status')
    @classmethod
    def validate_status(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in VALID_PROJECT_STATUSES:
            raise ValueError(f'Invalid status. Must be one of: {", ".join(VALID_PROJECT_STATUSES)}')
        return v
    
    @field_validator('color')
    @classmethod
    def validate_color(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not HEX_COLOR_PATTERN.match(v):
            raise ValueError('Invalid color format. Must be a valid hex color (e.g., #3B82F6)')
        return v.upper() if v else v

class ProjectResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    project_id: str
    org_id: str
    name: str
    description: Optional[str] = None
    status: str
    color: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    owner_id: str
    customer_id: Optional[str] = None
    task_statuses: List[Dict[str, Any]] = []
    task_count: int = 0
    completed_tasks: int = 0
    created_at: datetime
    updated_at: datetime
