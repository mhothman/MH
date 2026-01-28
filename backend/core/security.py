"""Security utilities - authentication and authorization"""
import bcrypt
import jwt
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, List
from fastapi import Request, HTTPException
import logging

from .config import settings
from .database import get_database
from .permissions import (
    Permission, 
    has_permission, 
    has_any_permission, 
    get_role_permissions,
    can_manage_role,
    ROLE_HIERARCHY
)

logger = logging.getLogger(__name__)

def hash_password(password: str) -> str:
    """Hash a password using bcrypt"""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_password(password: str, hashed: str) -> bool:
    """Verify a password against its hash"""
    try:
        return bcrypt.checkpw(password.encode(), hashed.encode())
    except Exception:
        return False

def create_jwt_token(user_id: str, email: str) -> str:
    """Create a JWT token for a user"""
    payload = {
        "user_id": user_id,
        "email": email,
        "exp": datetime.now(timezone.utc) + timedelta(hours=settings.JWT_EXPIRATION_HOURS),
        "iat": datetime.now(timezone.utc)
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)

def decode_jwt_token(token: str) -> Optional[Dict]:
    """Decode and validate a JWT token"""
    try:
        return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        logger.warning("Token expired")
        return None
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid token: {e}")
        return None

async def get_current_user(request: Request) -> Optional[Dict]:
    """Get the current authenticated user from request"""
    db = get_database()
    
    # Try Authorization header first
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        payload = decode_jwt_token(token)
        if payload:
            user = await db.users.find_one({"user_id": payload["user_id"]}, {"_id": 0, "password_hash": 0})
            if user and not user.get("suspended"):
                return user
    
    # Try session token from header
    session_token = request.headers.get("X-Session-Token")
    if session_token:
        session = await db.user_sessions.find_one({"session_token": session_token}, {"_id": 0})
        if session and datetime.fromisoformat(session["expires_at"].replace("Z", "+00:00")) > datetime.now(timezone.utc):
            user = await db.users.find_one({"user_id": session["user_id"]}, {"_id": 0, "password_hash": 0})
            if user and not user.get("suspended"):
                return user
    
    return None

async def require_auth(request: Request) -> Dict:
    """Require authentication - raises HTTPException if not authenticated"""
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user

async def get_user_org_membership(user_id: str, org_id: str) -> Optional[Dict]:
    """Get user's membership in an organization"""
    db = get_database()
    return await db.org_memberships.find_one(
        {"user_id": user_id, "org_id": org_id},
        {"_id": 0}
    )

async def require_org_role(request: Request, org_id: str, allowed_roles: list) -> Dict:
    """Require user to have specific role in organization"""
    user = await require_auth(request)
    membership = await get_user_org_membership(user["user_id"], org_id)
    
    if not membership or membership["role"] not in allowed_roles:
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    return user


async def require_permission(request: Request, org_id: str, permission: str) -> Dict:
    """
    Require user to have a specific permission in an organization.
    
    Args:
        request: FastAPI request object
        org_id: Organization ID
        permission: Permission string (e.g., Permission.PROJECT_CREATE)
        
    Returns:
        User dict if authorized
        
    Raises:
        HTTPException: 401 if not authenticated, 403 if no permission
    """
    user = await require_auth(request)
    membership = await get_user_org_membership(user["user_id"], org_id)
    
    if not membership:
        raise HTTPException(status_code=403, detail="Not a member of this organization")
    
    role = membership.get("role", "viewer")
    
    if not has_permission(role, permission):
        raise HTTPException(
            status_code=403, 
            detail=f"Permission denied. Required: {permission}"
        )
    
    # Add role and permissions to user for convenience
    user["_role"] = role
    user["_org_id"] = org_id
    user["_permissions"] = get_role_permissions(role)
    
    return user


async def require_any_permission(request: Request, org_id: str, permissions: List[str]) -> Dict:
    """
    Require user to have any one of the specified permissions.
    
    Args:
        request: FastAPI request object
        org_id: Organization ID
        permissions: List of permission strings
        
    Returns:
        User dict if authorized
    """
    user = await require_auth(request)
    membership = await get_user_org_membership(user["user_id"], org_id)
    
    if not membership:
        raise HTTPException(status_code=403, detail="Not a member of this organization")
    
    role = membership.get("role", "viewer")
    
    if not has_any_permission(role, permissions):
        raise HTTPException(
            status_code=403, 
            detail=f"Permission denied. Required one of: {', '.join(permissions)}"
        )
    
    user["_role"] = role
    user["_org_id"] = org_id
    user["_permissions"] = get_role_permissions(role)
    
    return user


async def check_permission(user_id: str, org_id: str, permission: str) -> bool:
    """
    Check if a user has a specific permission (non-raising version).
    
    Args:
        user_id: User ID
        org_id: Organization ID
        permission: Permission string
        
    Returns:
        True if user has permission, False otherwise
    """
    membership = await get_user_org_membership(user_id, org_id)
    if not membership:
        return False
    
    role = membership.get("role", "viewer")
    return has_permission(role, permission)


async def get_user_permissions(user_id: str, org_id: str) -> List[str]:
    """
    Get all permissions a user has in an organization.
    
    Args:
        user_id: User ID
        org_id: Organization ID
        
    Returns:
        List of permission strings
    """
    membership = await get_user_org_membership(user_id, org_id)
    if not membership:
        return []
    
    role = membership.get("role", "viewer")
    return get_role_permissions(role)


async def can_user_manage_member(manager_id: str, target_id: str, org_id: str) -> bool:
    """
    Check if a user can manage another member (change role, suspend, remove).
    
    A user can manage another member if:
    1. They have member management permissions
    2. Their role is higher in the hierarchy
    
    Args:
        manager_id: User ID of the manager
        target_id: User ID of the target member
        org_id: Organization ID
        
    Returns:
        True if manager can manage target, False otherwise
    """
    manager_membership = await get_user_org_membership(manager_id, org_id)
    target_membership = await get_user_org_membership(target_id, org_id)
    
    if not manager_membership or not target_membership:
        return False
    
    manager_role = manager_membership.get("role", "viewer")
    target_role = target_membership.get("role", "viewer")
    
    # Check if manager has permission and is higher in hierarchy
    has_perm = has_permission(manager_role, Permission.MEMBER_CHANGE_ROLE)
    is_higher = can_manage_role(manager_role, target_role)
    
    return has_perm and is_higher
