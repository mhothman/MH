"""Automation router - Refactored to use AutomationService"""
from fastapi import APIRouter, HTTPException, Request
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
import logging

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.database import get_database
from core.security import require_auth, get_user_org_membership
from core.permissions import Permission, has_permission
from models.feature_flag import Features
from services.feature_service import feature_service
from services.automation_service import automation_service, automation_engine

logger = logging.getLogger(__name__)
router = APIRouter()


# =============================================
# Pydantic Models
# =============================================

class TriggerConfig(BaseModel):
    """Automation trigger configuration"""
    type: str
    conditions: Dict[str, Any] = {}


class ActionConfig(BaseModel):
    """Automation action configuration"""
    type: str
    config: Dict[str, Any] = {}


class AutomationCreate(BaseModel):
    """Create automation request"""
    name: str
    description: Optional[str] = None
    trigger: TriggerConfig
    actions: List[ActionConfig]
    enabled: bool = True


class AutomationUpdate(BaseModel):
    """Update automation request"""
    name: Optional[str] = None
    description: Optional[str] = None
    trigger: Optional[TriggerConfig] = None
    actions: Optional[List[ActionConfig]] = None
    enabled: Optional[bool] = None


# =============================================
# Automation CRUD
# =============================================

@router.get("/org/{org_id}")
async def get_automations(org_id: str, request: Request):
    """Get all automations for an organization"""
    user = await require_auth(request)
    
    membership = await get_user_org_membership(user["user_id"], org_id)
    if not membership:
        raise HTTPException(status_code=403, detail="Access denied")
    
    if not has_permission(membership["role"], Permission.AUTOMATION_VIEW):
        raise HTTPException(status_code=403, detail="Permission denied: cannot view automations")
    
    if not await feature_service.is_enabled(org_id, Features.AUTOMATIONS):
        raise HTTPException(status_code=403, detail="Automations feature not available on your plan")
    
    automations = await automation_service.get_automations(org_id)
    return {"automations": automations}


@router.post("/org/{org_id}")
async def create_automation(org_id: str, data: AutomationCreate, request: Request):
    """Create a new automation"""
    db = get_database()
    user = await require_auth(request)
    
    membership = await get_user_org_membership(user["user_id"], org_id)
    if not membership:
        raise HTTPException(status_code=403, detail="Access denied")
    
    if not has_permission(membership["role"], Permission.AUTOMATION_CREATE):
        raise HTTPException(status_code=403, detail="Permission denied: cannot create automations")
    
    if not await feature_service.is_enabled(org_id, Features.AUTOMATIONS):
        raise HTTPException(status_code=403, detail="Automations feature not available on your plan")
    
    # Check limit
    current_count = await db.automations.count_documents({"org_id": org_id, "enabled": True})
    can_create = await feature_service.check_limit(org_id, "max_automations", current_count)
    if not can_create:
        raise HTTPException(status_code=403, detail="Automation limit reached for your plan")
    
    success, message, automation = await automation_service.create_automation(
        org_id=org_id,
        user_id=user["user_id"],
        name=data.name,
        description=data.description,
        trigger=data.trigger.model_dump(),
        actions=[a.model_dump() for a in data.actions],
        enabled=data.enabled
    )
    
    if not success:
        raise HTTPException(status_code=400, detail=message)
    
    return {"message": message, "automation_id": automation["automation_id"]}


@router.put("/{automation_id}")
async def update_automation(automation_id: str, data: AutomationUpdate, request: Request):
    """Update an automation"""
    user = await require_auth(request)
    
    automation = await automation_service.get_automation(automation_id)
    if not automation:
        raise HTTPException(status_code=404, detail="Automation not found")
    
    membership = await get_user_org_membership(user["user_id"], automation["org_id"])
    if not membership:
        raise HTTPException(status_code=403, detail="Access denied")
    
    if not has_permission(membership["role"], Permission.AUTOMATION_EDIT):
        raise HTTPException(status_code=403, detail="Permission denied: cannot edit automations")
    
    success, message = await automation_service.update_automation(
        automation_id=automation_id,
        user_id=user["user_id"],
        org_id=automation["org_id"],
        name=data.name,
        description=data.description,
        trigger=data.trigger.model_dump() if data.trigger else None,
        actions=[a.model_dump() for a in data.actions] if data.actions else None,
        enabled=data.enabled
    )
    
    if not success:
        raise HTTPException(status_code=400, detail=message)
    
    return {"message": message}


@router.delete("/{automation_id}")
async def delete_automation(automation_id: str, request: Request):
    """Delete an automation"""
    user = await require_auth(request)
    
    automation = await automation_service.get_automation(automation_id)
    if not automation:
        raise HTTPException(status_code=404, detail="Automation not found")
    
    membership = await get_user_org_membership(user["user_id"], automation["org_id"])
    if not membership:
        raise HTTPException(status_code=403, detail="Access denied")
    
    if not has_permission(membership["role"], Permission.AUTOMATION_DELETE):
        raise HTTPException(status_code=403, detail="Permission denied: cannot delete automations")
    
    success, message = await automation_service.delete_automation(
        automation_id, user["user_id"], automation["org_id"]
    )
    
    if not success:
        raise HTTPException(status_code=404, detail=message)
    
    return {"message": message}


@router.get("/{automation_id}/history")
async def get_automation_history(automation_id: str, request: Request, limit: int = 50):
    """Get execution history for an automation"""
    user = await require_auth(request)
    
    automation = await automation_service.get_automation(automation_id)
    if not automation:
        raise HTTPException(status_code=404, detail="Automation not found")
    
    membership = await get_user_org_membership(user["user_id"], automation["org_id"])
    if not membership:
        raise HTTPException(status_code=403, detail="Access denied")
    
    history = await automation_service.get_history(automation_id, limit)
    return {"history": history}


# =============================================
# Metadata Endpoints
# =============================================

@router.get("/triggers")
async def get_trigger_types():
    """Get available trigger types"""
    return {"triggers": automation_service.get_trigger_types()}


@router.get("/actions")
async def get_action_types():
    """Get available action types"""
    return {"actions": automation_service.get_action_types()}


# Export engine for use in other modules (task_router imports this)
__all__ = ["router", "automation_engine"]
