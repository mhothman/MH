"""Tenant Administration Router - Tenant-level management APIs"""
from fastapi import APIRouter, HTTPException, Request, Header
from typing import List, Optional
import logging
import jwt
from datetime import datetime, timezone, timedelta

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.config import settings
from core.database import get_database
from models.tenant import (
    TenantUserLogin,
    TenantUserCreate,
    TenantUserResponse,
    TenantResponse,
    OrganizationDetailResponse,
    OrganizationSuspendRequest,
    UserSuspendRequest,
    TenantUserManagementResponse
)
from services.tenant_service import tenant_service

logger = logging.getLogger(__name__)
router = APIRouter()


# ==================== Helper Functions ====================

def create_tenant_token(user: dict) -> str:
    """Create JWT token for tenant admin"""
    payload = {
        "user_id": user["user_id"],
        "email": user["email"],
        "role": user["role"],
        "type": "tenant_admin",  # Mark as tenant admin token
        "exp": datetime.now(timezone.utc) + timedelta(days=7),
        "iat": datetime.now(timezone.utc)
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")


async def require_tenant_admin(request: Request) -> dict:
    """Require tenant admin authentication"""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authentication required")
    
    token = auth_header.replace("Bearer ", "")
    
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
        
        # Verify this is a tenant admin token
        if payload.get("type") != "tenant_admin":
            raise HTTPException(status_code=403, detail="Tenant admin access required")
        
        # Get user from database
        db = get_database()
        user = await db.tenant_users.find_one(
            {"user_id": payload["user_id"]},
            {"_id": 0, "password_hash": 0}
        )
        
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        
        if user.get("status") != "active":
            raise HTTPException(status_code=403, detail="Account is suspended")
        
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


# ==================== Authentication ====================

@router.post("/auth/login")
async def tenant_admin_login(data: TenantUserLogin, request: Request):
    """Tenant admin login (separate from org users)"""
    success, user, message = await tenant_service.authenticate_tenant_user(
        email=data.email,
        password=data.password
    )
    
    if not success:
        raise HTTPException(status_code=401, detail=message)
    
    # Create token
    token = create_tenant_token(user)
    
    # Get tenant info
    tenant = await tenant_service.get_tenant(user["tenant_id"])
    
    return {
        "access_token": token,
        "token_type": "Bearer",
        "user": user,
        "tenant": tenant
    }


@router.get("/auth/me", response_model=TenantUserResponse)
async def get_tenant_admin_profile(request: Request):
    """Get current tenant admin profile"""
    user = await require_tenant_admin(request)
    return TenantUserResponse(**user)


@router.post("/auth/logout")
async def tenant_admin_logout(request: Request):
    """Tenant admin logout"""
    user = await require_tenant_admin(request)
    # Token invalidation can be added here
    return {"message": "Logged out successfully"}


# ==================== Organization Management ====================

@router.get("/organizations", response_model=List[OrganizationDetailResponse])
async def get_all_organizations(request: Request):
    """Get all organizations in the tenant"""
    user = await require_tenant_admin(request)
    
    orgs = await tenant_service.get_all_organizations(user["tenant_id"])
    
    # Convert to response model
    return [OrganizationDetailResponse(
        org_id=org["org_id"],
        tenant_id=org.get("tenant_id", user["tenant_id"]),
        name=org["name"],
        status=org.get("status", "active"),
        owner_id=org["owner_id"],
        owner_name=org.get("owner_name", "Unknown"),
        owner_email=org.get("owner_email", "Unknown"),
        total_members=org.get("total_members", 0),
        total_projects=org.get("total_projects", 0),
        total_tasks=org.get("total_tasks", 0),
        plan=org.get("plan", "free"),
        created_at=org.get("created_at") if isinstance(org.get("created_at"), datetime) else datetime.fromisoformat(org["created_at"]) if org.get("created_at") else datetime.now(timezone.utc),
        suspended_at=org.get("suspended_at"),
        suspended_by=org.get("suspended_by"),
        suspension_reason=org.get("suspension_reason")
    ) for org in orgs]


@router.get("/organizations/{org_id}", response_model=OrganizationDetailResponse)
async def get_organization_detail(org_id: str, request: Request):
    """Get detailed organization info"""
    user = await require_tenant_admin(request)
    
    org = await tenant_service.get_organization_detail(org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    return OrganizationDetailResponse(
        org_id=org["org_id"],
        tenant_id=org.get("tenant_id", user["tenant_id"]),
        name=org["name"],
        status=org.get("status", "active"),
        owner_id=org["owner_id"],
        owner_name=org.get("owner_name", "Unknown"),
        owner_email=org.get("owner_email", "Unknown"),
        total_members=org.get("total_members", 0),
        total_projects=org.get("total_projects", 0),
        total_tasks=org.get("total_tasks", 0),
        plan=org.get("plan", "free"),
        created_at=org.get("created_at") if isinstance(org.get("created_at"), datetime) else datetime.fromisoformat(org["created_at"]) if org.get("created_at") else datetime.now(timezone.utc),
        suspended_at=org.get("suspended_at"),
        suspended_by=org.get("suspended_by"),
        suspension_reason=org.get("suspension_reason")
    )


@router.post("/organizations/{org_id}/suspend")
async def suspend_organization(
    org_id: str,
    data: OrganizationSuspendRequest,
    request: Request
):
    """Suspend an organization"""
    user = await require_tenant_admin(request)
    
    # Get IP address
    ip_address = request.client.host if request.client else None
    
    success, message = await tenant_service.suspend_organization(
        org_id=org_id,
        suspended_by=user["user_id"],
        reason=data.reason,
        ip_address=ip_address
    )
    
    if not success:
        raise HTTPException(status_code=400, detail=message)
    
    return {"message": message}


@router.post("/organizations/{org_id}/activate")
async def activate_organization(org_id: str, request: Request):
    """Activate a suspended organization"""
    user = await require_tenant_admin(request)
    
    ip_address = request.client.host if request.client else None



@router.delete("/users/{user_id}")
async def delete_user(user_id: str, request: Request):
    """Permanently delete a user"""
    tenant_admin = await require_tenant_admin(request)
    
    ip_address = request.client.host if request.client else None
    
    success, message = await tenant_service.delete_user(
        user_id=user_id,
        deleted_by=tenant_admin["user_id"],
        ip_address=ip_address
    )
    
    if not success:
        raise HTTPException(status_code=400, detail=message)
    
    return {"message": message}

    
    success, message = await tenant_service.activate_organization(
        org_id=org_id,
        activated_by=user["user_id"],
        ip_address=ip_address
    )
    
    if not success:
        raise HTTPException(status_code=400, detail=message)
    
    return {"message": message}


# ==================== User Management ====================

@router.get("/organizations/{org_id}/users", response_model=List[TenantUserManagementResponse])
async def get_organization_users(org_id: str, request: Request):
    """Get all users in an organization"""
    user = await require_tenant_admin(request)
    
    users = await tenant_service.get_organization_users(org_id)
    return [TenantUserManagementResponse(**u) for u in users]


@router.post("/users/{user_id}/suspend")
async def suspend_user(
    user_id: str,
    data: UserSuspendRequest,
    request: Request
):
    """Suspend a user"""
    tenant_admin = await require_tenant_admin(request)
    
    ip_address = request.client.host if request.client else None
    
    success, message = await tenant_service.suspend_user(
        user_id=user_id,
        suspended_by=tenant_admin["user_id"],
        reason=data.reason,
        ip_address=ip_address
    )
    
    if not success:
        raise HTTPException(status_code=400, detail=message)
    
    return {"message": message}


@router.post("/users/{user_id}/activate")
async def activate_user(user_id: str, request: Request):
    """Activate a suspended user"""
    tenant_admin = await require_tenant_admin(request)
    
    ip_address = request.client.host if request.client else None
    
    success, message = await tenant_service.activate_user(
        user_id=user_id,
        activated_by=tenant_admin["user_id"],
        ip_address=ip_address
    )
    
    if not success:
        raise HTTPException(status_code=400, detail=message)
    
    return {"message": message}


# ==================== Initialization ====================

@router.post("/seed")
async def seed_tenant_data():
    """Seed initial tenant and super admin (one-time setup)"""
    result = await tenant_service.seed_initial_data()
    return result
