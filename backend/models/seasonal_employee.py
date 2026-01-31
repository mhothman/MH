"""Seasonal Employee Models - For temporary/seasonal workers without system access"""
from pydantic import BaseModel, field_validator, EmailStr
from typing import Optional
from datetime import datetime, date, time


# ==================== Seasonal Employee Models ====================

class SeasonalEmployeeCreate(BaseModel):
    """Model for creating a seasonal employee"""
    first_name: str
    second_name: str
    third_name: str
    national_id: str
    profession: str
    mobile_number: str
    email: Optional[str] = None
    
    @field_validator('first_name', 'second_name', 'third_name')
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError('Name fields are required')
        if len(v.strip()) > 100:
            raise ValueError('Name cannot exceed 100 characters')
        return v.strip()
    
    @field_validator('national_id')
    @classmethod
    def validate_national_id(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError('National ID is required')
        if len(v.strip()) > 50:
            raise ValueError('National ID cannot exceed 50 characters')
        return v.strip()
    
    @field_validator('profession')
    @classmethod
    def validate_profession(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError('Profession is required')
        return v.strip()
    
    @field_validator('mobile_number')
    @classmethod
    def validate_mobile(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError('Mobile number is required')
        return v.strip()


class SeasonalEmployeeUpdate(BaseModel):
    """Model for updating a seasonal employee"""
    first_name: Optional[str] = None
    second_name: Optional[str] = None
    third_name: Optional[str] = None
    profession: Optional[str] = None
    mobile_number: Optional[str] = None
    email: Optional[str] = None


class SeasonalEmployeeResponse(BaseModel):
    """Response model for seasonal employee"""
    employee_id: str
    tenant_id: str
    org_id: str
    first_name: str
    second_name: str
    third_name: str
    full_name: str
    national_id: str
    profession: str
    mobile_number: str
    email: Optional[str] = None
    total_projects: int = 0
    total_days_worked: int = 0
    total_cost: float = 0
    created_at: datetime
    created_by: str


# ==================== Project Assignment Models ====================

class SeasonalEmployeeProjectAssign(BaseModel):
    """Model for assigning seasonal employee to project"""
    seasonal_employee_id: str
    project_id: str
    day_rate: float
    start_date: str  # YYYY-MM-DD
    end_date: str  # YYYY-MM-DD
    
    @field_validator('day_rate')
    @classmethod
    def validate_day_rate(cls, v: float) -> float:
        if v <= 0:
            raise ValueError('Day rate must be positive')
        if v > 999999:
            raise ValueError('Day rate exceeds maximum')
        return round(v, 2)
    
    @field_validator('start_date', 'end_date')
    @classmethod
    def validate_date_format(cls, v: str) -> str:
        try:
            datetime.strptime(v, '%Y-%m-%d')
            return v
        except ValueError:
            raise ValueError('Date must be in YYYY-MM-DD format')


class SeasonalEmployeeProjectUpdate(BaseModel):
    """Model for updating project assignment"""
    day_rate: Optional[float] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None


class SeasonalEmployeeProjectResponse(BaseModel):
    """Response model for project assignment"""
    assignment_id: str
    seasonal_employee_id: str
    employee_name: str
    project_id: str
    project_name: str
    day_rate: float
    start_date: str
    end_date: str
    days_worked: int = 0
    total_cost: float = 0
    assigned_by: str
    assigned_by_name: str
    created_at: datetime


# ==================== Attendance Models ====================

class AttendanceCreate(BaseModel):
    """Model for creating attendance record"""
    seasonal_employee_project_id: str
    work_date: str  # YYYY-MM-DD
    time_in: str  # HH:MM
    time_out: str  # HH:MM
    
    @field_validator('work_date')
    @classmethod
    def validate_work_date(cls, v: str) -> str:
        try:
            datetime.strptime(v, '%Y-%m-%d')
            return v
        except ValueError:
            raise ValueError('Work date must be in YYYY-MM-DD format')
    
    @field_validator('time_in', 'time_out')
    @classmethod
    def validate_time(cls, v: str) -> str:
        try:
            datetime.strptime(v, '%H:%M')
            return v
        except ValueError:
            raise ValueError('Time must be in HH:MM format (24-hour)')


class AttendanceUpdate(BaseModel):
    """Model for updating attendance"""
    time_in: Optional[str] = None
    time_out: Optional[str] = None


class AttendanceResponse(BaseModel):
    """Response model for attendance"""
    attendance_id: str
    assignment_id: str
    employee_name: str
    project_name: str
    work_date: str
    time_in: str
    time_out: str
    hours_worked: float
    created_by: str
    created_by_name: str
    created_at: datetime


# ==================== Summary Models ====================

class SeasonalEmployeeCostSummary(BaseModel):
    """Cost summary for seasonal employee"""
    employee_id: str
    employee_name: str
    total_projects: int
    total_days_worked: int
    total_hours_worked: float
    total_cost: float
    assignments: list
