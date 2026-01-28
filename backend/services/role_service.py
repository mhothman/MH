"""Role Service - Business logic for role management"""
from datetime import datetime, timezone
from typing import List, Dict, Optional, Tuple
import uuid
import logging

from core.database import get_database
from core.permissions import ROLE_PERMISSIONS, has_permission, Permission
from services.audit_service import audit_service

logger = logging.getLogger(__name__)


# All available permissions
ALL_PERMISSIONS = [
    # Project
    {"id": "project:view", "name": "View Projects", "category": "Projects"},
    {"id": "project:create", "name": "Create Projects", "category": "Projects"},
    {"id": "project:edit", "name": "Edit Projects", "category": "Projects"},
    {"id": "project:delete", "name": "Delete Projects", "category": "Projects"},
    {"id": "project:archive", "name": "Archive Projects", "category": "Projects"},
    {"id": "project:manage_team", "name": "Manage Project Team", "category": "Projects"},
    # Tasks
    {"id": "task:view", "name": "View Tasks", "category": "Tasks"},
    {"id": "task:create", "name": "Create Tasks", "category": "Tasks"},
    {"id": "task:edit", "name": "Edit Any Task", "category": "Tasks"},
    {"id": "task:edit_own", "name": "Edit Own Tasks", "category": "Tasks"},
    {"id": "task:delete", "name": "Delete Tasks", "category": "Tasks"},
    {"id": "task:assign", "name": "Assign Tasks", "category": "Tasks"},
    {"id": "task:change_status", "name": "Change Task Status", "category": "Tasks"},
    # Members
    {"id": "member:view", "name": "View Members", "category": "Team"},
    {"id": "member:invite", "name": "Invite Members", "category": "Team"},
    {"id": "member:remove", "name": "Remove Members", "category": "Team"},
    {"id": "member:change_role", "name": "Change Member Roles", "category": "Team"},
    {"id": "member:suspend", "name": "Suspend Members", "category": "Team"},
    {"id": "member:reset_password", "name": "Reset Passwords", "category": "Team"},
    # Customers
    {"id": "customer:view", "name": "View Customers", "category": "Customers"},
    {"id": "customer:create", "name": "Create Customers", "category": "Customers"},
    {"id": "customer:edit", "name": "Edit Customers", "category": "Customers"},
    {"id": "customer:delete", "name": "Delete Customers", "category": "Customers"},
    # Reports
    {"id": "report:view", "name": "View Reports", "category": "Reports"},
    {"id": "report:export", "name": "Export Reports", "category": "Reports"},
    {"id": "report:executive", "name": "Executive Dashboard", "category": "Reports"},
    # Settings
    {"id": "settings:view", "name": "View Settings", "category": "Settings"},
    {"id": "settings:edit", "name": "Edit Settings", "category": "Settings"},
    {"id": "settings:billing", "name": "Manage Billing", "category": "Settings"},
    # Automations
    {"id": "automation:view", "name": "View Automations", "category": "Automations"},
    {"id": "automation:create", "name": "Create Automations", "category": "Automations"},
    {"id": "automation:edit", "name": "Edit Automations", "category": "Automations"},
    {"id": "automation:delete", "name": "Delete Automations", "category": "Automations"},
    # Audit
    {"id": "audit:view", "name": "View Audit Logs", "category": "Audit"},
    {"id": "audit:export", "name": "Export Audit Logs", "category": "Audit"},
    # Comments
    {"id": "comment:view", "name": "View Comments", "category": "Comments"},
    {"id": "comment:create", "name": "Create Comments", "category": "Comments"},
    {"id": "comment:edit_own", "name": "Edit Own Comments", "category": "Comments"},
    {"id": "comment:delete_any", "name": "Delete Any Comment", "category": "Comments"},
    # Time Tracking
    {"id": "time:view_own", "name": "View Own Time", "category": "Time Tracking"},
    {"id": "time:view_all", "name": "View All Time Entries", "category": "Time Tracking"},
    {"id": "time:create", "name": "Create Time Entries", "category": "Time Tracking"},
    {"id": "time:edit_own", "name": "Edit Own Time Entries", "category": "Time Tracking"},
    # Workflow
    {"id": "workflow:view", "name": "View Workflows", "category": "Workflows"},
    {"id": "workflow:create", "name": "Create Workflows", "category": "Workflows"},
    {"id": "workflow:edit", "name": "Edit Workflows", "category": "Workflows"},
    {"id": "workflow:delete", "name": "Delete Workflows", "category": "Workflows"},
    {"id": "workflow:assign", "name": "Assign Workflows to Projects", "category": "Workflows"},
    # Approvals
    {"id": "approval:view", "name": "View Approvals", "category": "Approvals"},
    {"id": "approval:request", "name": "Request Approvals", "category": "Approvals"},
    {"id": "approval:approve", "name": "Approve Requests", "category": "Approvals"},
    {"id": "approval:reject", "name": "Reject Requests", "category": "Approvals"},
    {"id": "approval:force", "name": "Force Approve/Reject", "category": "Approvals"},
]

BUILT_IN_ROLES = ["super_admin", "org_admin", "project_manager", "team_member", "viewer"]

ROLE_DESCRIPTIONS = {
    "super_admin": "Full system access with all permissions",
    "org_admin": "Full access to organization settings and members",
    "project_manager": "Manage projects, tasks, and team assignments",
    "team_member": "Work on tasks, add comments, track time",
    "viewer": "Read-only access to projects and tasks",
}

ROLE_COLORS = {
    "super_admin": "#dc2626",
    "org_admin": "#7c3aed",
    "project_manager": "#2563eb",
    "team_member": "#16a34a",
    "viewer": "#6b7280",
}


class RoleService:
    """Service for role management business logic"""
    
    def __init__(self):
        self.valid_perm_ids = {p["id"] for p in ALL_PERMISSIONS}
    
    # =============================================
    # Permission Queries
    # =============================================
    
    def get_all_permissions(self) -> Dict:
        """Get all available permissions grouped by category"""
        categories = {}
        for perm in ALL_PERMISSIONS:
            cat = perm["category"]
            if cat not in categories:
                categories[cat] = []
            categories[cat].append({
                "id": perm["id"],
                "name": perm["name"]
            })
        
        return {
            "permissions": ALL_PERMISSIONS,
            "categories": categories
        }
    
    def validate_permissions(self, permissions: List[str]) -> Tuple[bool, str]:
        """Validate that all permissions are valid"""
        for perm in permissions:
            if perm not in self.valid_perm_ids:
                return False, f"Invalid permission: {perm}"
        return True, ""
    
    # =============================================
    # Built-in Roles
    # =============================================
    
    async def get_all_roles(self, org_id: str) -> Dict:
        """Get all roles (built-in + custom) for an organization"""
        db = get_database()
        
        # Get built-in role overrides for this org
        overrides = {}
        async for override in db.builtin_role_overrides.find({"org_id": org_id}, {"_id": 0}):
            overrides[override["role_name"]] = override
        
        # Build built-in roles with overrides
        built_in = []
        for role_key, default_perms in ROLE_PERMISSIONS.items():
            override = overrides.get(role_key, {})
            built_in.append({
                "role_id": role_key,
                "name": role_key.replace("_", " ").title(),
                "key": role_key,
                "description": override.get("description") or ROLE_DESCRIPTIONS.get(role_key, ""),
                "permissions": override.get("permissions") or default_perms,
                "is_built_in": True,
                "color": override.get("color") or ROLE_COLORS.get(role_key, "#6366f1"),
                "member_count": await self._get_builtin_role_member_count(db, org_id, role_key)
            })
        
        # Get custom roles
        custom_roles = await db.custom_roles.find({"org_id": org_id}, {"_id": 0}).to_list(100)
        for role in custom_roles:
            role["is_built_in"] = False
            role["member_count"] = await self._get_custom_role_member_count(db, org_id, role["role_id"])
        
        return {
            "built_in_roles": built_in,
            "custom_roles": custom_roles
        }
    
    async def update_builtin_role(
        self,
        org_id: str,
        role_name: str,
        user_id: str,
        user_role: str,
        permissions: List[str] = None,
        description: str = None,
        color: str = None
    ) -> Tuple[bool, str]:
        """Update built-in role permissions for an organization"""
        db = get_database()
        
        # Validate role name
        if role_name not in BUILT_IN_ROLES:
            return False, "Invalid built-in role name"
        
        # Only super_admin can modify built-in roles
        if user_role != "super_admin":
            return False, "Only Super Admins can modify built-in roles"
        
        # Validate permissions if provided
        if permissions is not None:
            valid, error = self.validate_permissions(permissions)
            if not valid:
                return False, error
        
        now = datetime.now(timezone.utc).isoformat()
        
        update_data = {"updated_at": now}
        if permissions is not None:
            update_data["permissions"] = permissions
        if description is not None:
            update_data["description"] = description
        if color is not None:
            update_data["color"] = color
        
        await db.builtin_role_overrides.update_one(
            {"org_id": org_id, "role_name": role_name},
            {"$set": update_data, "$setOnInsert": {"created_at": now}},
            upsert=True
        )
        
        await audit_service.log(
            org_id=org_id,
            user_id=user_id,
            action="update_builtin_role",
            resource_type="builtin_role",
            resource_id=role_name,
            details={"updated_fields": list(update_data.keys())}
        )
        
        return True, f"Built-in role '{role_name}' updated successfully"
    
    # =============================================
    # Custom Roles
    # =============================================
    
    async def create_custom_role(
        self,
        org_id: str,
        user_id: str,
        name: str,
        permissions: List[str],
        description: str = None,
        color: str = None
    ) -> Tuple[bool, str, Optional[Dict]]:
        """Create a new custom role"""
        db = get_database()
        
        # Validate permissions
        valid, error = self.validate_permissions(permissions)
        if not valid:
            return False, error, None
        
        # Check for duplicate name
        existing = await db.custom_roles.find_one({
            "org_id": org_id,
            "name": {"$regex": f"^{name}$", "$options": "i"}
        })
        if existing:
            return False, "A role with this name already exists", None
        
        role_id = f"role_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc).isoformat()
        
        role = {
            "role_id": role_id,
            "org_id": org_id,
            "name": name,
            "description": description or "",
            "permissions": permissions,
            "color": color or "#6366f1",
            "created_by": user_id,
            "created_at": now,
            "updated_at": now,
        }
        
        await db.custom_roles.insert_one(role)
        role.pop("_id", None)
        
        await audit_service.log(
            org_id=org_id,
            user_id=user_id,
            action="create",
            resource_type="custom_role",
            resource_id=role_id,
            details={"name": name, "permissions_count": len(permissions)}
        )
        
        role["is_built_in"] = False
        role["member_count"] = 0
        return True, "Role created successfully", role
    
    async def get_custom_role(self, role_id: str) -> Optional[Dict]:
        """Get a specific custom role"""
        db = get_database()
        role = await db.custom_roles.find_one({"role_id": role_id}, {"_id": 0})
        if role:
            role["is_built_in"] = False
            role["member_count"] = await self._get_custom_role_member_count(db, role["org_id"], role_id)
        return role
    
    async def update_custom_role(
        self,
        role_id: str,
        user_id: str,
        name: str = None,
        permissions: List[str] = None,
        description: str = None,
        color: str = None
    ) -> Tuple[bool, str, Optional[Dict]]:
        """Update a custom role"""
        db = get_database()
        
        role = await db.custom_roles.find_one({"role_id": role_id}, {"_id": 0})
        if not role:
            return False, "Role not found", None
        
        # Validate permissions if provided
        if permissions is not None:
            valid, error = self.validate_permissions(permissions)
            if not valid:
                return False, error, None
        
        # Check for duplicate name if changing
        if name and name.lower() != role["name"].lower():
            existing = await db.custom_roles.find_one({
                "org_id": role["org_id"],
                "name": {"$regex": f"^{name}$", "$options": "i"},
                "role_id": {"$ne": role_id}
            })
            if existing:
                return False, "A role with this name already exists", None
        
        update_data = {"updated_at": datetime.now(timezone.utc).isoformat()}
        if name is not None:
            update_data["name"] = name
        if description is not None:
            update_data["description"] = description
        if permissions is not None:
            update_data["permissions"] = permissions
        if color is not None:
            update_data["color"] = color
        
        await db.custom_roles.update_one({"role_id": role_id}, {"$set": update_data})
        
        await audit_service.log(
            org_id=role["org_id"],
            user_id=user_id,
            action="update",
            resource_type="custom_role",
            resource_id=role_id,
            details={"updated_fields": list(update_data.keys())}
        )
        
        updated_role = await db.custom_roles.find_one({"role_id": role_id}, {"_id": 0})
        updated_role["is_built_in"] = False
        updated_role["member_count"] = await self._get_custom_role_member_count(db, role["org_id"], role_id)
        return True, "Role updated successfully", updated_role
    
    async def delete_custom_role(self, role_id: str, user_id: str) -> Tuple[bool, str]:
        """Delete a custom role"""
        db = get_database()
        
        role = await db.custom_roles.find_one({"role_id": role_id}, {"_id": 0})
        if not role:
            return False, "Role not found"
        
        # Check if any members have this role
        member_count = await self._get_custom_role_member_count(db, role["org_id"], role_id)
        if member_count > 0:
            return False, f"Cannot delete role: {member_count} member(s) are assigned to this role. Reassign them first."
        
        await db.custom_roles.delete_one({"role_id": role_id})
        
        await audit_service.log(
            org_id=role["org_id"],
            user_id=user_id,
            action="delete",
            resource_type="custom_role",
            resource_id=role_id,
            details={"name": role["name"]}
        )
        
        return True, "Role deleted successfully"
    
    async def get_role_members(self, role_id: str) -> List[Dict]:
        """Get members assigned to a custom role"""
        db = get_database()
        
        role = await db.custom_roles.find_one({"role_id": role_id}, {"_id": 0})
        if not role:
            return []
        
        memberships = await db.org_memberships.find({
            "org_id": role["org_id"],
            "custom_role_id": role_id
        }, {"_id": 0}).to_list(100)
        
        if not memberships:
            return []
        
        user_ids = [m["user_id"] for m in memberships]
        users = await db.users.find(
            {"user_id": {"$in": user_ids}},
            {"_id": 0, "user_id": 1, "name": 1, "email": 1, "picture": 1}
        ).to_list(len(user_ids))
        
        return users
    
    # =============================================
    # Helper Methods
    # =============================================
    
    async def _get_builtin_role_member_count(self, db, org_id: str, role: str) -> int:
        """Get count of members with a built-in role"""
        return await db.org_memberships.count_documents({
            "org_id": org_id,
            "role": role
        })
    
    async def _get_custom_role_member_count(self, db, org_id: str, role_id: str) -> int:
        """Get count of members with a custom role"""
        return await db.org_memberships.count_documents({
            "org_id": org_id,
            "custom_role_id": role_id
        })


# Singleton instance
role_service = RoleService()
