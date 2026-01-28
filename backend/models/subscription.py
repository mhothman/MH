"""Subscription and billing models"""
from pydantic import BaseModel, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

class PlanType(str, Enum):
    FREE = "free"
    STARTER = "starter"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"

class SubscriptionStatus(str, Enum):
    ACTIVE = "active"
    CANCELLED = "cancelled"
    PAST_DUE = "past_due"
    TRIALING = "trialing"
    PAUSED = "paused"

class SubscriptionPlan(BaseModel):
    """Subscription plan definition"""
    model_config = ConfigDict(extra="ignore")
    
    plan_id: str
    name: str
    type: str  # free, starter, professional, enterprise
    price_monthly: float
    price_yearly: float
    features: List[str] = []
    limits: Dict[str, int] = {}
    description: Optional[str] = None
    is_active: bool = True
    created_at: datetime
    updated_at: datetime

class OrganizationSubscription(BaseModel):
    """Organization's active subscription"""
    model_config = ConfigDict(extra="ignore")
    
    subscription_id: str
    org_id: str
    plan_id: str
    plan_type: str
    status: str = "active"
    billing_cycle: str = "monthly"  # monthly or yearly
    current_period_start: datetime
    current_period_end: datetime
    cancel_at_period_end: bool = False
    trial_end: Optional[datetime] = None
    stripe_subscription_id: Optional[str] = None
    stripe_customer_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime

class SubscriptionCreate(BaseModel):
    plan_id: str
    billing_cycle: str = "monthly"

class UsageRecord(BaseModel):
    """Track usage for metered billing"""
    model_config = ConfigDict(extra="ignore")
    
    record_id: str
    org_id: str
    metric: str  # projects, members, storage_mb, automations_run
    quantity: int
    recorded_at: datetime

# Default plans configuration
DEFAULT_PLANS = [
    {
        "plan_id": "plan_free",
        "name": "Free",
        "type": "free",
        "price_monthly": 0,
        "price_yearly": 0,
        "description": "Perfect for individuals and small teams getting started",
        "features": [],
        "limits": {
            "max_projects": 3,
            "max_members": 5,
            "max_storage_mb": 100,
            "max_automations": 0
        }
    },
    {
        "plan_id": "plan_starter",
        "name": "Starter",
        "type": "starter",
        "price_monthly": 12,
        "price_yearly": 120,
        "description": "For growing teams that need more power",
        "features": ["audit_logs", "data_export"],
        "limits": {
            "max_projects": 10,
            "max_members": 15,
            "max_storage_mb": 1000,
            "max_automations": 5
        }
    },
    {
        "plan_id": "plan_professional",
        "name": "Professional",
        "type": "professional",
        "price_monthly": 29,
        "price_yearly": 290,
        "description": "For teams that need advanced features",
        "features": [
            "audit_logs", "data_export", "advanced_rbac",
            "automations", "webhooks", "advanced_reports"
        ],
        "limits": {
            "max_projects": 50,
            "max_members": 50,
            "max_storage_mb": 10000,
            "max_automations": 25
        }
    },
    {
        "plan_id": "plan_enterprise",
        "name": "Enterprise",
        "type": "enterprise",
        "price_monthly": 99,
        "price_yearly": 990,
        "description": "For large organizations with custom needs",
        "features": "all",
        "limits": {
            "max_projects": -1,
            "max_members": -1,
            "max_storage_mb": -1,
            "max_automations": -1
        }
    }
]
