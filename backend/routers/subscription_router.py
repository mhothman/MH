"""Subscription management router"""
from fastapi import APIRouter, HTTPException, Request
from typing import List
import logging

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.security import require_auth, get_user_org_membership
from models.enums import UserRole
from services.subscription_service import subscription_service
from services.feature_service import feature_service
from services.audit_service import audit_service

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/plans")
async def get_subscription_plans():
    """Get all available subscription plans"""
    return await subscription_service.get_plans()

@router.get("/org/{org_id}")
async def get_org_subscription(org_id: str, request: Request):
    """Get organization's current subscription"""
    user = await require_auth(request)
    
    membership = await get_user_org_membership(user["user_id"], org_id)
    if not membership:
        raise HTTPException(status_code=403, detail="Access denied")
    
    subscription = await subscription_service.get_org_subscription(org_id)
    features = await feature_service.get_org_features(org_id)
    usage = await subscription_service.get_usage_summary(org_id)
    
    return {
        "subscription": subscription,
        "features": features,
        "usage": usage
    }

@router.post("/org/{org_id}/upgrade")
async def upgrade_subscription(org_id: str, plan_id: str, billing_cycle: str, request: Request):
    """Upgrade organization's subscription"""
    user = await require_auth(request)
    
    membership = await get_user_org_membership(user["user_id"], org_id)
    if not membership or membership["role"] not in [UserRole.ORG_ADMIN, UserRole.SUPER_ADMIN]:
        raise HTTPException(status_code=403, detail="Only admins can manage subscriptions")
    
    subscription = await subscription_service.upgrade_plan(org_id, plan_id, billing_cycle)
    
    await audit_service.log(user["user_id"], org_id, "update", "subscription", subscription["subscription_id"])
    
    return {"message": "Subscription updated", "subscription": subscription}

@router.post("/org/{org_id}/cancel")
async def cancel_subscription(org_id: str, immediate: bool = False, request: Request = None):
    """Cancel organization's subscription"""
    user = await require_auth(request)
    
    membership = await get_user_org_membership(user["user_id"], org_id)
    if not membership or membership["role"] not in [UserRole.ORG_ADMIN, UserRole.SUPER_ADMIN]:
        raise HTTPException(status_code=403, detail="Only admins can manage subscriptions")
    
    success = await subscription_service.cancel_subscription(org_id, immediate)
    
    if success:
        await audit_service.log(user["user_id"], org_id, "delete", "subscription", org_id)
        return {"message": "Subscription cancelled"}
    
    raise HTTPException(status_code=404, detail="No active subscription found")
