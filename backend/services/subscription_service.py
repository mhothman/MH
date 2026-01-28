"""Subscription management service"""
import uuid
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict

from core.database import get_database
from models.subscription import DEFAULT_PLANS, PlanType, SubscriptionStatus

logger = logging.getLogger(__name__)

class SubscriptionService:
    """Service for managing organization subscriptions"""
    
    @staticmethod
    async def initialize_plans():
        """Initialize default plans in database"""
        db = get_database()
        
        for plan in DEFAULT_PLANS:
            existing = await db.plans.find_one({"plan_id": plan["plan_id"]})
            if not existing:
                plan["is_active"] = True
                plan["created_at"] = datetime.now(timezone.utc).isoformat()
                plan["updated_at"] = datetime.now(timezone.utc).isoformat()
                await db.plans.insert_one(plan)
                logger.info(f"Initialized plan: {plan['name']}")
    
    @staticmethod
    async def get_plans() -> List[Dict]:
        """Get all active subscription plans"""
        db = get_database()
        cursor = db.plans.find({"is_active": True}, {"_id": 0})
        return await cursor.to_list(None)
    
    @staticmethod
    async def get_plan(plan_id: str) -> Optional[Dict]:
        """Get a specific plan by ID"""
        db = get_database()
        return await db.plans.find_one({"plan_id": plan_id}, {"_id": 0})
    
    @staticmethod
    async def get_org_subscription(org_id: str) -> Optional[Dict]:
        """Get active subscription for an organization"""
        db = get_database()
        return await db.subscriptions.find_one(
            {"org_id": org_id, "status": {"$in": ["active", "trialing"]}},
            {"_id": 0}
        )
    
    @staticmethod
    async def create_subscription(
        org_id: str,
        plan_id: str,
        billing_cycle: str = "monthly",
        trial_days: int = 0
    ) -> Dict:
        """
        Create a subscription for an organization.
        
        Args:
            org_id: Organization ID
            plan_id: Plan ID
            billing_cycle: 'monthly' or 'yearly'
            trial_days: Number of trial days (0 for no trial)
            
        Returns:
            Created subscription record
        """
        db = get_database()
        
        # Get plan details
        plan = await SubscriptionService.get_plan(plan_id)
        if not plan:
            raise ValueError(f"Plan {plan_id} not found")
        
        # Cancel any existing subscription
        await db.subscriptions.update_many(
            {"org_id": org_id, "status": {"$in": ["active", "trialing"]}},
            {"$set": {"status": "cancelled", "cancelled_at": datetime.now(timezone.utc).isoformat()}}
        )
        
        subscription_id = f"sub_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc)
        
        # Calculate period
        if billing_cycle == "yearly":
            period_end = now + timedelta(days=365)
        else:
            period_end = now + timedelta(days=30)
        
        subscription = {
            "subscription_id": subscription_id,
            "org_id": org_id,
            "plan_id": plan_id,
            "plan_type": plan["type"],
            "status": "trialing" if trial_days > 0 else "active",
            "billing_cycle": billing_cycle,
            "current_period_start": now.isoformat(),
            "current_period_end": period_end.isoformat(),
            "trial_end": (now + timedelta(days=trial_days)).isoformat() if trial_days > 0 else None,
            "cancel_at_period_end": False,
            "stripe_subscription_id": None,
            "stripe_customer_id": None,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat()
        }
        
        await db.subscriptions.insert_one(subscription)
        logger.info(f"Created subscription {subscription_id} for org {org_id}")
        
        return subscription
    
    @staticmethod
    async def create_free_subscription(org_id: str) -> Dict:
        """Create a free plan subscription for a new organization"""
        return await SubscriptionService.create_subscription(
            org_id=org_id,
            plan_id="plan_free",
            billing_cycle="monthly"
        )
    
    @staticmethod
    async def upgrade_plan(
        org_id: str,
        new_plan_id: str,
        billing_cycle: str = "monthly"
    ) -> Dict:
        """Upgrade organization to a new plan"""
        return await SubscriptionService.create_subscription(
            org_id=org_id,
            plan_id=new_plan_id,
            billing_cycle=billing_cycle
        )
    
    @staticmethod
    async def cancel_subscription(org_id: str, immediate: bool = False) -> bool:
        """
        Cancel an organization's subscription.
        
        Args:
            org_id: Organization ID
            immediate: If True, cancel immediately. If False, cancel at period end.
        """
        db = get_database()
        
        if immediate:
            result = await db.subscriptions.update_one(
                {"org_id": org_id, "status": {"$in": ["active", "trialing"]}},
                {
                    "$set": {
                        "status": "cancelled",
                        "cancelled_at": datetime.now(timezone.utc).isoformat(),
                        "updated_at": datetime.now(timezone.utc).isoformat()
                    }
                }
            )
        else:
            result = await db.subscriptions.update_one(
                {"org_id": org_id, "status": {"$in": ["active", "trialing"]}},
                {
                    "$set": {
                        "cancel_at_period_end": True,
                        "updated_at": datetime.now(timezone.utc).isoformat()
                    }
                }
            )
        
        if result.modified_count > 0:
            logger.info(f"Subscription cancelled for org {org_id} (immediate={immediate})")
            return True
        return False
    
    @staticmethod
    async def record_usage(org_id: str, metric: str, quantity: int = 1):
        """Record usage for metered billing"""
        db = get_database()
        
        record = {
            "record_id": f"usage_{uuid.uuid4().hex[:12]}",
            "org_id": org_id,
            "metric": metric,
            "quantity": quantity,
            "recorded_at": datetime.now(timezone.utc).isoformat()
        }
        
        await db.usage_records.insert_one(record)
    
    @staticmethod
    async def get_usage_summary(org_id: str) -> Dict:
        """Get usage summary for an organization"""
        db = get_database()
        
        # Count current resources
        projects_count = await db.projects.count_documents({"org_id": org_id})
        members_count = await db.org_memberships.count_documents({"org_id": org_id})
        
        # Calculate storage (simplified - would need actual file size tracking)
        attachments = await db.attachments.find({"org_id": org_id}).to_list(None)
        storage_mb = sum(a.get("size", 0) for a in attachments) / (1024 * 1024)
        
        # Count automations
        automations_count = await db.automations.count_documents({"org_id": org_id, "enabled": True})
        
        return {
            "projects": projects_count,
            "members": members_count,
            "storage_mb": round(storage_mb, 2),
            "automations": automations_count
        }

# Singleton instance
subscription_service = SubscriptionService()
