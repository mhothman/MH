"""Custom Role Management Router - Refactored to use RoleService"""
from fastapi import APIRouter, HTTPException, Request
from typing import List, Optional

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.security import require_auth, get_user_org_membership
from core.permissions import Permission, has_permission
from core.cache import cache, CacheKeys
from services.role_service import role_service
from models.role import CustomRoleCreate, CustomRoleUpdate, BuiltInRoleUpdate

router = APIRouter(prefix="/roles", tags=["roles"])


# =============================================
# Permission Endpoints
# =============================================

@router.get("/permissions")
async def get_all_permissions(request: Request):
    """Get all available permissions grouped by category"""
    await require_auth(request)
    
    cache_key = CacheKeys.PERMISSIONS
    cached = cache.get(cache_key)
    if cached:
        return cached
    
    result = role_service.get_all_permissions()
    cache.set(cache_key, result)
    return result


# =============================================
# Role List Endpoints
# =============================================

@router.get("/org/{org_id}")
async def get_roles(org_id: str, request: Request):
    """Get all roles for an organization (built-in + custom)"""
    user = await require_auth(request)
    
    membership = await get_user_org_membership(user["user_id"], org_id)
    if not membership:
        raise HTTPException(status_code=403, detail="Access denied")
    
    if not has_permission(membership["role"], Permission.SETTINGS_VIEW):
        raise HTTPException(status_code=403, detail="Permission denied: cannot view roles")
    
    return await role_service.get_all_roles(org_id)


# =============================================
# Custom Role CRUD
# =============================================

@router.post("/org/{org_id}")
async def create_custom_role(org_id: str, data: CustomRoleCreate, request: Request):
    """Create a new custom role for an organization"""
    user = await require_auth(request)
    
    membership = await get_user_org_membership(user["user_id"], org_id)
    if not membership:
        raise HTTPException(status_code=403, detail="Access denied")
    
    if not has_permission(membership["role"], Permission.SETTINGS_EDIT):
        raise HTTPException(status_code=403, detail="Permission denied: cannot create roles")
    
    success, message, role = await role_service.create_custom_role(
        org_id=org_id,
        user_id=user["user_id"],
        name=data.name,
        permissions=data.permissions,
        description=data.description,
        color=data.color
    )
    
    if not success:
        raise HTTPException(status_code=400, detail=message)
    
    return role


@router.get("/{role_id}")
async def get_role(role_id: str, request: Request):
    """Get a specific custom role"""
    user = await require_auth(request)
    
    role = await role_service.get_custom_role(role_id)
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    
    membership = await get_user_org_membership(user["user_id"], role["org_id"])
    if not membership:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return role


@router.put("/{role_id}")
async def update_custom_role(role_id: str, data: CustomRoleUpdate, request: Request):
    """Update a custom role"""
    user = await require_auth(request)
    
    role = await role_service.get_custom_role(role_id)
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    
    membership = await get_user_org_membership(user["user_id"], role["org_id"])
    if not membership:
        raise HTTPException(status_code=403, detail="Access denied")
    
    if not has_permission(membership["role"], Permission.SETTINGS_EDIT):
        raise HTTPException(status_code=403, detail="Permission denied: cannot edit roles")
    
    success, message, updated_role = await role_service.update_custom_role(
        role_id=role_id,
        user_id=user["user_id"],
        name=data.name,
        permissions=data.permissions,
        description=data.description,
        color=data.color
    )
    
    if not success:
        raise HTTPException(status_code=400, detail=message)
    
    return updated_role


@router.delete("/{role_id}")
async def delete_custom_role(role_id: str, request: Request):
    """Delete a custom role"""
    user = await require_auth(request)
    
    role = await role_service.get_custom_role(role_id)
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    
    membership = await get_user_org_membership(user["user_id"], role["org_id"])
    if not membership:
        raise HTTPException(status_code=403, detail="Access denied")
    
    if not has_permission(membership["role"], Permission.SETTINGS_EDIT):
        raise HTTPException(status_code=403, detail="Permission denied: cannot delete roles")
    
    success, message = await role_service.delete_custom_role(role_id, user["user_id"])
    
    if not success:
        raise HTTPException(status_code=400, detail=message)
    
    return {"message": message}


# =============================================
# Built-in Role Management
# =============================================

@router.put("/builtin/{role_name}/org/{org_id}")
async def update_builtin_role(role_name: str, org_id: str, data: BuiltInRoleUpdate, request: Request):
    """Update built-in role permissions for an organization (super_admin only)"""
    user = await require_auth(request)
    
    membership = await get_user_org_membership(user["user_id"], org_id)
    if not membership:
        raise HTTPException(status_code=403, detail="Access denied")
    
    success, message = await role_service.update_builtin_role(
        org_id=org_id,
        role_name=role_name,
        user_id=user["user_id"],
        user_role=membership["role"],
        permissions=data.permissions,
        description=data.description,
        color=data.color
    )
    
    if not success:
        raise HTTPException(status_code=403 if "Super Admin" in message else 400, detail=message)
    
    return {"message": message}


# =============================================
# Role Members
# =============================================

@router.get("/{role_id}/members")
async def get_role_members(role_id: str, request: Request):
    """Get members assigned to a custom role"""
    user = await require_auth(request)
    
    role = await role_service.get_custom_role(role_id)
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    
    membership = await get_user_org_membership(user["user_id"], role["org_id"])
    if not membership:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return await role_service.get_role_members(role_id)
