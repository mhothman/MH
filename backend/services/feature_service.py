"""Feature flag service for controlling feature access"""
import logging
from typing import Optional, List, Dict
from datetime import datetime, timezone

from core.database import get_database
from models.feature_flag import Features, DEFAULT_PLAN_FEATURES

logger = logging.getLogger(__name__)

class FeatureService:
    """Service for checking and managing feature flags"""
    
    # TEMPORARY: Enable all features for all users during development
    ENABLE_ALL_FEATURES = True
    
    @staticmethod
    async def is_enabled(org_id: str, feature: str) -> bool:
        """
        Check if a feature is enabled for an organization.
        
        Args:
            org_id: Organization ID
            feature: Feature flag name (from Features class)
            
        Returns:
            True if feature is enabled, False otherwise
        """
        # TEMPORARY: Enable all features during development
        if FeatureService.ENABLE_ALL_FEATURES:
            return True
            
        db = get_database()
        
        # Get organization's subscription
        subscription = await db.subscriptions.find_one(
            {"org_id": org_id, "status": "active"},
            {"_id": 0}
        )
        
        if not subscription:
            # Default to free plan
            plan_type = "free"
        else:
            plan_type = subscription.get("plan_type", "free")
        
        # Check if feature is included in plan
        plan_config = DEFAULT_PLAN_FEATURES.get(plan_type, DEFAULT_PLAN_FEATURES["free"])
        
        # Enterprise has all features
        if plan_type == "enterprise":
            return True
        
        # Check plan features
        if feature in plan_config.get("features", []):
            return True
        
        # Check for custom feature overrides
        org_features = await db.org_features.find_one({"org_id": org_id}, {"_id": 0})
        if org_features and feature in org_features.get("enabled_features", []):
            return True
        
        return False
    
    @staticmethod
    async def get_org_features(org_id: str) -> Dict:
        """
        Get all features and their status for an organization.
        
        Returns:
            Dict with feature names as keys and enabled status as values
        """
        db = get_database()
        
        # Get subscription
        subscription = await db.subscriptions.find_one(
            {"org_id": org_id, "status": "active"},
            {"_id": 0}
        )
        
        plan_type = subscription.get("plan_type", "free") if subscription else "free"
        plan_config = DEFAULT_PLAN_FEATURES.get(plan_type, DEFAULT_PLAN_FEATURES["free"])
        
        # Get custom overrides
        org_features = await db.org_features.find_one({"org_id": org_id}, {"_id": 0})
        custom_features = org_features.get("enabled_features", []) if org_features else []
        
        # Build feature map
        features = {}
        for feature in Features.all():
            if plan_type == "enterprise":
                features[feature] = True
            elif feature in plan_config.get("features", []):
                features[feature] = True
            elif feature in custom_features:
                features[feature] = True
            else:
                features[feature] = False
        
        return {
            "plan_type": plan_type,
            "features": features,
            "limits": plan_config.get("limits", {})
        }
    
    @staticmethod
    async def get_limit(org_id: str, limit_name: str) -> int:
        """
        Get a specific limit for an organization.
        
        Args:
            org_id: Organization ID
            limit_name: Limit name (max_projects, max_members, etc.)
            
        Returns:
            Limit value (-1 for unlimited)
        """
        db = get_database()
        
        subscription = await db.subscriptions.find_one(
            {"org_id": org_id, "status": "active"},
            {"_id": 0}
        )
        
        plan_type = subscription.get("plan_type", "free") if subscription else "free"
        plan_config = DEFAULT_PLAN_FEATURES.get(plan_type, DEFAULT_PLAN_FEATURES["free"])
        
        # Check for custom limit overrides
        org_features = await db.org_features.find_one({"org_id": org_id}, {"_id": 0})
        if org_features and limit_name in org_features.get("custom_limits", {}):
            return org_features["custom_limits"][limit_name]
        
        return plan_config.get("limits", {}).get(limit_name, 0)
    
    @staticmethod
    async def check_limit(org_id: str, limit_name: str, current_usage: int) -> bool:
        """
        Check if an organization is within their limit.
        
        Args:
            org_id: Organization ID
            limit_name: Limit name
            current_usage: Current usage count
            
        Returns:
            True if within limit, False if exceeded
        """
        # TEMPORARY: Bypass limits during development
        if FeatureService.ENABLE_ALL_FEATURES:
            return True
            
        limit = await FeatureService.get_limit(org_id, limit_name)
        
        # -1 means unlimited
        if limit == -1:
            return True
        
        return current_usage < limit
    
    @staticmethod
    async def enable_feature(org_id: str, feature: str) -> bool:
        """Enable a feature for an organization (admin override)"""
        db = get_database()
        
        await db.org_features.update_one(
            {"org_id": org_id},
            {
                "$addToSet": {"enabled_features": feature},
                "$set": {"updated_at": datetime.now(timezone.utc).isoformat()}
            },
            upsert=True
        )
        
        logger.info(f"Feature {feature} enabled for org {org_id}")
        return True
    
    @staticmethod
    async def disable_feature(org_id: str, feature: str) -> bool:
        """Disable a feature for an organization"""
        db = get_database()
        
        await db.org_features.update_one(
            {"org_id": org_id},
            {
                "$pull": {"enabled_features": feature},
                "$set": {"updated_at": datetime.now(timezone.utc).isoformat()}
            }
        )
        
        logger.info(f"Feature {feature} disabled for org {org_id}")
        return True
    
    @staticmethod
    async def set_custom_limit(org_id: str, limit_name: str, value: int) -> bool:
        """Set a custom limit for an organization"""
        db = get_database()
        
        await db.org_features.update_one(
            {"org_id": org_id},
            {
                "$set": {
                    f"custom_limits.{limit_name}": value,
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }
            },
            upsert=True
        )
        
        logger.info(f"Custom limit {limit_name}={value} set for org {org_id}")
        return True

# Singleton instance  
feature_service = FeatureService()
