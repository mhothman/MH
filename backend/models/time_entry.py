"""Time entry and timer models with validation"""
from pydantic import BaseModel, ConfigDict, field_validator, Field
from typing import Optional
from datetime import datetime


class TimeEntryCreate(BaseModel):
    """Model for creating a manual time entry"""
    task_id: str
    duration_minutes: int = Field(..., gt=0, description="Duration in minutes (must be positive)")
    description: Optional[str] = None
    date: Optional[str] = None
    
    @field_validator('task_id')
    @classmethod
    def task_id_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError('Task ID is required')
        return v.strip()
    
    @field_validator('duration_minutes')
    @classmethod
    def validate_duration(cls, v: int) -> int:
        if v <= 0:
            raise ValueError('Duration must be positive')
        if v > 1440:  # 24 hours max
            raise ValueError('Duration cannot exceed 24 hours (1440 minutes)')
        return v
    
    @field_validator('description')
    @classmethod
    def validate_description(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            if len(v) > 1000:
                raise ValueError('Description cannot exceed 1000 characters')
            return v.strip() if v.strip() else None
        return v


class TimeEntryUpdate(BaseModel):
    """Model for updating a time entry"""
    duration_minutes: Optional[int] = None
    description: Optional[str] = None
    date: Optional[str] = None
    
    @field_validator('duration_minutes')
    @classmethod
    def validate_duration(cls, v: Optional[int]) -> Optional[int]:
        if v is not None:
            if v <= 0:
                raise ValueError('Duration must be positive')
            if v > 1440:
                raise ValueError('Duration cannot exceed 24 hours (1440 minutes)')
        return v
    
    @field_validator('description')
    @classmethod
    def validate_description(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and len(v) > 1000:
            raise ValueError('Description cannot exceed 1000 characters')
        return v


class TimerStart(BaseModel):
    """Model for starting a timer"""
    task_id: str
    description: Optional[str] = None
    
    @field_validator('task_id')
    @classmethod
    def task_id_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError('Task ID is required')
        return v.strip()
    
    @field_validator('description')
    @classmethod
    def validate_description(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and len(v) > 1000:
            raise ValueError('Description cannot exceed 1000 characters')
        return v


class TimeEntryResponse(BaseModel):
    """Response model for time entries"""
    model_config = ConfigDict(extra="ignore")
    
    entry_id: str
    task_id: str
    user_id: str
    org_id: str
    duration_minutes: int
    description: Optional[str] = None
    date: str
    created_at: datetime
    updated_at: datetime


class TimerResponse(BaseModel):
    """Response model for active timer"""
    model_config = ConfigDict(extra="ignore")
    
    timer_id: str
    task_id: str
    user_id: str
    org_id: str
    started_at: str
    description: Optional[str] = None
    is_running: bool
    elapsed_seconds: int = 0
