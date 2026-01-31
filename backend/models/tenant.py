"""Tenant models - Multi-tenant administration"""
from pydantic import BaseModel, field_validator, EmailStr
from typing import Optional
from datetime import datetime
from enum import Enum


class TenantStatus(str, Enum):
    """Tenant status values"""
    ACTIVE = "active"
    SUSPENDED = "suspended"
    INACTIVE = "inactive"


class TenantUserRole(str, Enum):
    """Tenant-level roles (separate from organization roles)"""
    TENANT_SUPER_ADMIN = "tenant_super_admin"
    TENANT_ADMIN = "tenant_admin"


class TenantUserStatus(str, Enum):
    """Tenant user status"""
    ACTIVE = "active"
    SUSPENDED = "suspended"


# ==================== Tenant Models ====================

class TenantCreate(BaseModel):
    """Model for creating a tenant"""
    name: str
    domain: Optional[str] = None
    
    @field_validator('name')
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError('Tenant name is required')
        if len(v.strip()) > 100:
            raise ValueError('Tenant name cannot exceed 100 characters')
        return v.strip()


class TenantResponse(BaseModel):
    """Response model for tenant"""
    tenant_id: str
    name: str
    domain: Optional[str] = None
    status: str
    total_organizations: int = 0
    total_users: int = 0
    created_at: datetime


# ==================== Tenant User Models ====================

class TenantUserCreate(BaseModel):
    """Model for creating a tenant user"""
    email: EmailStr
    password: str
    name: str
    role: TenantUserRole = TenantUserRole.TENANT_ADMIN
    
    @field_validator('password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        return v
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError('Name is required')
        return v.strip()


class TenantUserLogin(BaseModel):
    """Model for tenant admin login"""
    email: EmailStr
    password: str


class TenantUserResponse(BaseModel):
    """Response model for tenant user"""
    user_id: str
    tenant_id: str
    email: str
    name: str
    role: str
    status: str
    last_login: Optional[datetime] = None
    created_at: datetime


# ==================== Organization Management Models ====================

class OrganizationSuspendRequest(BaseModel):
    """Model for suspending/activating an organization"""
    reason: Optional[str] = None


class OrganizationDetailResponse(BaseModel):
    """Detailed organization response for tenant admins"""
    org_id: str
    tenant_id: str
    name: str
    status: str
    owner_id: str
    owner_name: str
    owner_email: str
    total_members: int
    total_projects: int
    total_tasks: int
    plan: Optional[str] = "free"
    created_at: datetime
    suspended_at: Optional[datetime] = None
    suspended_by: Optional[str] = None
    suspension_reason: Optional[str] = None


class UserSuspendRequest(BaseModel):
    """Model for suspending/activating a user"""
    reason: Optional[str] = None


class TenantUserManagementResponse(BaseModel):
    """User info for tenant admin view"""
    user_id: str
    email: str
    name: str
    org_id: str
    org_name: str
    role: str
    status: str
    last_login: Optional[datetime] = None
    created_at: datetime
    suspended_at: Optional[datetime] = None
    suspended_by: Optional[str] = None
