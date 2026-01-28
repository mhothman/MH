"""Feature flag models for enterprise features"""
from pydantic import BaseModel, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime

class FeatureFlag(BaseModel):
    """Individual feature flag definition"""
    model_config = ConfigDict(extra="ignore")
    
    flag_id: str
    name: str
    description: Optional[str] = None
    default_enabled: bool = False
    plans: List[str] = []  # Which plans have access
    created_at: datetime
    updated_at: datetime

class FeatureFlagCreate(BaseModel):
    name: str
    description: Optional[str] = None
    default_enabled: bool = False
    plans: List[str] = []

# Pre-defined feature flags
class Features:
    """Feature flag constants"""
    # Auth & Governance
    ADVANCED_RBAC = "advanced_rbac"
    CUSTOM_ROLES = "custom_roles"
    AUDIT_LOGS = "audit_logs"
    DATA_EXPORT = "data_export"
    RETENTION_POLICIES = "retention_policies"
    
    # Automation
    AUTOMATIONS = "automations"
    WEBHOOKS = "webhooks"
    SCHEDULED_TASKS = "scheduled_tasks"
    
    # Reporting
    ADVANCED_REPORTS = "advanced_reports"
    SCHEDULED_REPORTS = "scheduled_reports"
    EXECUTIVE_DASHBOARDS = "executive_dashboards"
    
    # Limits
    UNLIMITED_PROJECTS = "unlimited_projects"
    UNLIMITED_MEMBERS = "unlimited_members"
    UNLIMITED_STORAGE = "unlimited_storage"
    
    @classmethod
    def all(cls):
        return [
            cls.ADVANCED_RBAC, cls.CUSTOM_ROLES, cls.AUDIT_LOGS,
            cls.DATA_EXPORT, cls.RETENTION_POLICIES, cls.AUTOMATIONS,
            cls.WEBHOOKS, cls.SCHEDULED_TASKS, cls.ADVANCED_REPORTS,
            cls.SCHEDULED_REPORTS, cls.EXECUTIVE_DASHBOARDS,
            cls.UNLIMITED_PROJECTS, cls.UNLIMITED_MEMBERS, cls.UNLIMITED_STORAGE
        ]

class OrganizationFeatures(BaseModel):
    """Feature flags enabled for an organization"""
    model_config = ConfigDict(extra="ignore")
    
    org_id: str
    enabled_features: List[str] = []
    custom_limits: Dict[str, Any] = {}
    updated_at: datetime

# Default feature limits per plan
DEFAULT_PLAN_FEATURES = {
    "free": {
        "features": [],
        "limits": {
            "max_projects": 3,
            "max_members": 5,
            "max_storage_mb": 100,
            "max_automations": 0
        }
    },
    "starter": {
        "features": [Features.AUDIT_LOGS, Features.DATA_EXPORT],
        "limits": {
            "max_projects": 10,
            "max_members": 15,
            "max_storage_mb": 1000,
            "max_automations": 5
        }
    },
    "professional": {
        "features": [
            Features.AUDIT_LOGS, Features.DATA_EXPORT,
            Features.ADVANCED_RBAC, Features.AUTOMATIONS,
            Features.WEBHOOKS, Features.ADVANCED_REPORTS
        ],
        "limits": {
            "max_projects": 50,
            "max_members": 50,
            "max_storage_mb": 10000,
            "max_automations": 25
        }
    },
    "enterprise": {
        "features": Features.all(),
        "limits": {
            "max_projects": -1,  # Unlimited
            "max_members": -1,
            "max_storage_mb": -1,
            "max_automations": -1
        }
    }
}
