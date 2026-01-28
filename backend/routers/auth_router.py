"""Authentication router"""
from fastapi import APIRouter, HTTPException, Request, Response
from datetime import datetime, timezone, timedelta
from typing import List
import uuid
import logging

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.database import get_database
from core.security import (
    hash_password, verify_password, create_jwt_token, decode_jwt_token, 
    require_auth, get_user_org_membership, get_user_permissions
)
from core.permissions import Permission, get_role_permissions, ROLE_PERMISSIONS
from core.config import settings
from models.user import UserCreate, UserLogin, UserResponse, TokenResponse
from models.auth import PasswordResetRequest, PasswordResetConfirm
from models.enums import UserRole
from services.email_service import email_service
from services.audit_service import audit_service

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/register", response_model=TokenResponse)
async def register(data: UserCreate):
    """Register a new user"""
    db = get_database()
    
    # Check if user exists
    existing = await db.users.find_one({"email": data.email}, {"_id": 0})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Check for invitation token
    invitation = None
    if data.invitation_token:
        invitation = await db.invitations.find_one({
            "token": data.invitation_token,
            "accepted": False
        }, {"_id": 0})
        if not invitation:
            raise HTTPException(status_code=400, detail="Invalid or expired invitation")
        if invitation["email"].lower() != data.email.lower():
            raise HTTPException(status_code=400, detail="Email does not match invitation")
    
    # Require organization_name if no invitation
    if not invitation and not data.organization_name:
        raise HTTPException(status_code=400, detail="Organization name is required")
    
    user_id = f"user_{uuid.uuid4().hex[:12]}"
    user = {
        "user_id": user_id,
        "email": data.email,
        "name": data.name,
        "password_hash": hash_password(data.password),
        "picture": None,
        "role": UserRole.TEAM_MEMBER,
        "email_verified": False,
        "suspended": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.users.insert_one(user)
    
    if invitation:
        # Join the invited organization
        membership = {
            "membership_id": f"mem_{uuid.uuid4().hex[:12]}",
            "user_id": user_id,
            "org_id": invitation["org_id"],
            "role": invitation["role"],
            "joined_at": datetime.now(timezone.utc).isoformat()
        }
        await db.org_memberships.insert_one(membership)
        
        # Mark invitation as accepted
        await db.invitations.update_one(
            {"token": data.invitation_token},
            {"$set": {"accepted": True, "accepted_at": datetime.now(timezone.utc).isoformat()}}
        )
        
        # Subscription module disabled - skip subscription creation
    else:
        # Create default organization for user
        org_id = f"org_{uuid.uuid4().hex[:12]}"
        org = {
            "org_id": org_id,
            "name": data.organization_name,
            "logo": None,
            "timezone": "UTC",
            "working_days": ["monday", "tuesday", "wednesday", "thursday", "friday"],
            "owner_id": user_id,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.organizations.insert_one(org)
        
        # Add user as org admin
        membership = {
            "membership_id": f"mem_{uuid.uuid4().hex[:12]}",
            "user_id": user_id,
            "org_id": org_id,
            "role": UserRole.ORG_ADMIN,
            "joined_at": datetime.now(timezone.utc).isoformat()
        }
        await db.org_memberships.insert_one(membership)
        
        # Subscription module disabled - skip subscription creation
        
        # Audit log
        await audit_service.log(user_id, org_id, "create", "organization", org_id)
    
    token = create_jwt_token(user_id, data.email)
    
    user_response = await db.users.find_one({"user_id": user_id}, {"_id": 0, "password_hash": 0})
    user_response["created_at"] = datetime.fromisoformat(user_response["created_at"])
    
    return TokenResponse(
        access_token=token,
        user=UserResponse(**user_response)
    )

@router.post("/login", response_model=TokenResponse)
async def login(data: UserLogin, response: Response):
    """Login with email and password"""
    db = get_database()
    
    user = await db.users.find_one({"email": data.email}, {"_id": 0})
    if not user or not verify_password(data.password, user.get("password_hash", "")):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    if user.get("suspended"):
        raise HTTPException(status_code=403, detail="Account suspended")
    
    # Create session
    session_token = f"sess_{uuid.uuid4().hex}"
    session = {
        "session_token": session_token,
        "user_id": user["user_id"],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "expires_at": (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat(),
        "user_agent": None,
        "ip_address": None
    }
    await db.user_sessions.insert_one(session)
    
    # Set cookie
    response.set_cookie(
        key="session_token",
        value=session_token,
        httponly=True,
        secure=True,
        samesite="none",
        max_age=86400
    )
    
    token = create_jwt_token(user["user_id"], user["email"])
    
    user["created_at"] = datetime.fromisoformat(user["created_at"]) if isinstance(user["created_at"], str) else user["created_at"]
    del user["password_hash"]
    
    return TokenResponse(access_token=token, user=UserResponse(**user))

@router.get("/me", response_model=UserResponse)
async def get_me(request: Request):
    """Get current user info"""
    user = await require_auth(request)
    user["created_at"] = datetime.fromisoformat(user["created_at"]) if isinstance(user["created_at"], str) else user["created_at"]
    return UserResponse(**user)

@router.post("/logout")
async def logout(request: Request, response: Response):
    """Logout user"""
    db = get_database()
    
    session_token = request.headers.get("X-Session-Token")
    if session_token:
        await db.user_sessions.delete_one({"session_token": session_token})
    
    response.delete_cookie(key="session_token")
    return {"message": "Logged out successfully"}

@router.post("/password-reset-request")
async def request_password_reset(data: PasswordResetRequest):
    """Request password reset email"""
    db = get_database()
    
    user = await db.users.find_one({"email": data.email}, {"_id": 0})
    if user:
        reset_token = f"rst_{uuid.uuid4().hex}"
        reset_data = {
            "token": reset_token,
            "user_id": user["user_id"],
            "email": data.email,
            "expires_at": (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat(),
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        await db.password_resets.insert_one(reset_data)
        
        reset_link = f"{settings.APP_URL}/reset-password?token={reset_token}"
        await email_service.send_password_reset(data.email, reset_link, user["name"])
    
    return {"message": "If the email exists, a reset link will be sent"}

@router.post("/password-reset-confirm")
async def confirm_password_reset(data: PasswordResetConfirm):
    """Confirm password reset with token"""
    db = get_database()
    
    reset = await db.password_resets.find_one({"token": data.token}, {"_id": 0})
    if not reset:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")
    
    if datetime.fromisoformat(reset["expires_at"].replace("Z", "+00:00")) < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Reset token has expired")
    
    await db.users.update_one(
        {"user_id": reset["user_id"]},
        {"$set": {"password_hash": hash_password(data.new_password)}}
    )
    
    await db.password_resets.delete_one({"token": data.token})
    
    return {"message": "Password reset successful"}

@router.get("/session")
async def get_session(request: Request, response: Response):
    """Get current session info"""
    from core.security import get_current_user
    
    user = await get_current_user(request)
    if user:
        user["created_at"] = datetime.fromisoformat(user["created_at"]) if isinstance(user["created_at"], str) else user["created_at"]
        return {"authenticated": True, "user": UserResponse(**user)}
    
    return {"authenticated": False, "user": None}


@router.get("/permissions/{org_id}")
async def get_my_permissions(org_id: str, request: Request):
    """Get current user's permissions for an organization"""
    user = await require_auth(request)
    
    permissions = await get_user_permissions(user["user_id"], org_id)
    membership = await get_user_org_membership(user["user_id"], org_id)
    
    if not membership:
        raise HTTPException(status_code=403, detail="Not a member of this organization")
    
    return {
        "role": membership.get("role", "viewer"),
        "permissions": permissions
    }

@router.get("/roles")
async def get_all_roles():
    """Get all available roles and their permissions"""
    return {
        "roles": [
            {
                "key": role,
                "name": role.replace("_", " ").title(),
                "permissions": perms
            }
            for role, perms in ROLE_PERMISSIONS.items()
        ]
    }

