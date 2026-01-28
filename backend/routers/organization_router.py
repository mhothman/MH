"""Organization management router - Refactored to use OrganizationService"""
from fastapi import APIRouter, HTTPException, Request
from typing import List

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.security import (
    require_auth, 
    require_permission, 
    get_user_org_membership,
    can_user_manage_member
)
from core.permissions import Permission
from models.organization import (
    OrganizationCreate, 
    OrganizationResponse, 
    InviteCreate, 
    ChangeRoleRequest, 
    OrganizationUpdate,
    DomainConfigRequest,
    DomainVerificationResponse
)
from models.enums import UserRole
from services.organization_service import organization_service

router = APIRouter()


# =============================================
# Organization CRUD
# =============================================

@router.get("/", response_model=List[OrganizationResponse])
async def get_organizations(request: Request):
    """Get all organizations for the current user"""
    user = await require_auth(request)
    orgs = await organization_service.get_user_organizations(user["user_id"])
    return [OrganizationResponse(**org) for org in orgs]


@router.post("/", response_model=OrganizationResponse)
async def create_organization(data: OrganizationCreate, request: Request):
    """Create a new organization - DISABLED"""
    raise HTTPException(
        status_code=403,
        detail="Creating additional organizations is not allowed. Each user can only have one organization."
    )


@router.get("/{org_id}", response_model=OrganizationResponse)
async def get_organization(org_id: str, request: Request):
    """Get organization by ID"""
    user = await require_auth(request)
    
    membership = await get_user_org_membership(user["user_id"], org_id)
    if not membership:
        raise HTTPException(status_code=403, detail="Access denied")
    
    org = await organization_service.get_organization(org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    return OrganizationResponse(**org)


@router.put("/{org_id}", response_model=OrganizationResponse)
async def update_organization(org_id: str, data: OrganizationUpdate, request: Request):
    """Update organization settings"""
    user = await require_permission(request, org_id, Permission.SETTINGS_EDIT)
    
    org = await organization_service.update_organization(
        org_id=org_id,
        user_id=user["user_id"],
        name=data.name,
        logo=data.logo,
        timezone_str=data.timezone,
        working_days=data.working_days,
        address=data.address,
        contact_phone=data.contact_phone,
        contact_email=data.contact_email
    )
    
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    return OrganizationResponse(**org)


# =============================================
# Member Management
# =============================================

@router.get("/{org_id}/members")
async def get_organization_members(org_id: str, request: Request):
    """Get all members of an organization"""
    user = await require_auth(request)
    
    membership = await get_user_org_membership(user["user_id"], org_id)
    if not membership:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return await organization_service.get_members(org_id)


@router.post("/{org_id}/invite")
async def invite_member(org_id: str, data: InviteCreate, request: Request):
    """Invite a user to the organization"""
    user = await require_permission(request, org_id, Permission.MEMBER_INVITE)
    
    success, message = await organization_service.invite_member(
        org_id=org_id,
        inviter_id=user["user_id"],
        inviter_name=user["name"],
        email=data.email,
        role=data.role
    )
    
    if not success:
        raise HTTPException(status_code=400, detail=message)
    
    return {"message": message}


@router.post("/{org_id}/members/{user_id}/remove")
async def remove_member(org_id: str, user_id: str, request: Request):
    """Remove a member from the organization"""
    current_user = await require_permission(request, org_id, Permission.MEMBER_REMOVE)
    
    if user_id == current_user["user_id"]:
        raise HTTPException(status_code=400, detail="Cannot remove yourself")
    
    can_manage = await can_user_manage_member(current_user["user_id"], user_id, org_id)
    if not can_manage:
        raise HTTPException(status_code=403, detail="Cannot remove a member with equal or higher role")
    
    success, message = await organization_service.remove_member(org_id, user_id, current_user["user_id"])
    
    if not success:
        raise HTTPException(status_code=404 if "not found" in message else 400, detail=message)
    
    return {"message": message}


@router.post("/{org_id}/members/{user_id}/suspend")
async def suspend_member(org_id: str, user_id: str, request: Request):
    """Suspend a member in the organization"""
    current_user = await require_permission(request, org_id, Permission.MEMBER_SUSPEND)
    
    if user_id == current_user["user_id"]:
        raise HTTPException(status_code=400, detail="Cannot suspend yourself")
    
    can_manage = await can_user_manage_member(current_user["user_id"], user_id, org_id)
    if not can_manage:
        raise HTTPException(status_code=403, detail="Cannot suspend a member with equal or higher role")
    
    success, message = await organization_service.suspend_member(org_id, user_id, current_user["user_id"])
    
    if not success:
        raise HTTPException(status_code=404, detail=message)
    
    return {"message": message}


@router.post("/{org_id}/members/{user_id}/unsuspend")
async def unsuspend_member(org_id: str, user_id: str, request: Request):
    """Unsuspend a member in the organization"""
    current_user = await require_permission(request, org_id, Permission.MEMBER_SUSPEND)
    
    success, message = await organization_service.unsuspend_member(org_id, user_id, current_user["user_id"])
    
    if not success:
        raise HTTPException(status_code=404, detail=message)
    
    return {"message": message}


@router.post("/{org_id}/members/{user_id}/change-role")
async def change_member_role(org_id: str, user_id: str, data: ChangeRoleRequest, request: Request):
    """Change a member's role in the organization"""
    current_user = await require_permission(request, org_id, Permission.MEMBER_CHANGE_ROLE)
    
    if user_id == current_user["user_id"]:
        raise HTTPException(status_code=400, detail="Cannot change your own role")
    
    can_manage = await can_user_manage_member(current_user["user_id"], user_id, org_id)
    if not can_manage:
        raise HTTPException(status_code=403, detail="Cannot change role of a member with equal or higher role")
    
    success, message = await organization_service.change_member_role(
        org_id=org_id,
        user_id=user_id,
        admin_id=current_user["user_id"],
        role=data.role,
        custom_role_id=data.custom_role_id
    )
    
    if not success:
        raise HTTPException(
            status_code=404 if "not found" in message else 400, 
            detail=message
        )
    
    return {"message": message}


@router.post("/{org_id}/members/{user_id}/reset-password")
async def admin_reset_password(org_id: str, user_id: str, request: Request):
    """Admin resets password for a member"""
    current_user = await require_permission(request, org_id, Permission.MEMBER_RESET_PASSWORD)
    
    success, message = await organization_service.reset_member_password(
        org_id, user_id, current_user["user_id"]
    )
    
    if not success:
        raise HTTPException(status_code=404, detail=message)
    
    return {"message": message}


# =============================================
# Invitations
# =============================================

@router.get("/{org_id}/invitations")
async def get_pending_invitations(org_id: str, request: Request):
    """Get all pending invitations for an organization"""
    current_user = await require_auth(request)
    
    membership = await get_user_org_membership(current_user["user_id"], org_id)
    if not membership:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return await organization_service.get_pending_invitations(org_id)


@router.post("/{org_id}/invitations/resend")
async def resend_invitation(org_id: str, request: Request, email: str = None):
    """Resend invitation email"""
    current_user = await require_auth(request)
    
    membership = await get_user_org_membership(current_user["user_id"], org_id)
    if not membership or membership["role"] not in [UserRole.ORG_ADMIN, UserRole.SUPER_ADMIN]:
        raise HTTPException(status_code=403, detail="Only admins can resend invitations")
    
    success, message = await organization_service.resend_invitation(
        org_id, email, current_user["user_id"], current_user["name"]
    )
    
    if not success:
        raise HTTPException(status_code=404, detail=message)
    
    return {"message": message}


@router.delete("/{org_id}/invitations/{invite_id}")
async def cancel_invitation(org_id: str, invite_id: str, request: Request):
    """Cancel a pending invitation"""
    current_user = await require_auth(request)
    
    membership = await get_user_org_membership(current_user["user_id"], org_id)
    if not membership or membership["role"] not in [UserRole.ORG_ADMIN, UserRole.SUPER_ADMIN]:
        raise HTTPException(status_code=403, detail="Only admins can cancel invitations")
    
    success, message = await organization_service.cancel_invitation(org_id, invite_id)
    
    if not success:
        raise HTTPException(status_code=404, detail=message)
    
    return {"message": message}


# =============================================
# White-Label Domain Management
# =============================================

@router.get("/{org_id}/domain", response_model=DomainVerificationResponse)
async def get_domain_config(org_id: str, request: Request):
    """Get current domain configuration and verification status"""
    await require_permission(request, org_id, Permission.SETTINGS_VIEW)
    
    config = await organization_service.get_domain_config(org_id)
    if not config:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    return DomainVerificationResponse(**config)


@router.post("/{org_id}/domain")
async def configure_domain(org_id: str, data: DomainConfigRequest, request: Request):
    """Configure a custom domain for the organization"""
    user = await require_permission(request, org_id, Permission.SETTINGS_EDIT)
    
    success, message, result = await organization_service.configure_domain(
        org_id, user["user_id"], data.custom_domain
    )
    
    if not success:
        raise HTTPException(status_code=400, detail=message)
    
    return {"message": message, **result}


@router.post("/{org_id}/domain/verify")
async def verify_domain(org_id: str, request: Request):
    """Verify domain ownership by checking DNS TXT record"""
    user = await require_permission(request, org_id, Permission.SETTINGS_EDIT)
    
    result = await organization_service.verify_domain(org_id, user["user_id"])
    return result


@router.delete("/{org_id}/domain")
async def remove_domain(org_id: str, request: Request):
    """Remove custom domain configuration"""
    user = await require_permission(request, org_id, Permission.SETTINGS_EDIT)
    
    success, message = await organization_service.remove_domain(org_id, user["user_id"])
    
    if not success:
        raise HTTPException(status_code=404, detail=message)
    
    return {"message": message}
