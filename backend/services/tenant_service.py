"""Tenant Administration Service - Manage tenants, organizations, and users"""
import logging
from datetime import datetime, timezone
from typing import List, Dict, Optional, Tuple
from uuid import uuid4
import bcrypt

from core.database import get_database
from services.audit_service import audit_service

logger = logging.getLogger(__name__)


class TenantService:
    """Service for tenant-level administration"""
    
    # ==================== Tenant Management ====================
    
    async def create_tenant(self, name: str, domain: Optional[str] = None) -> Dict:
        """Create a new tenant"""
        db = get_database()
        
        tenant_id = f"tenant_{uuid4().hex[:12]}"
        now = datetime.now(timezone.utc).isoformat()
        
        tenant = {
            "tenant_id": tenant_id,
            "name": name,
            "domain": domain,
            "status": "active",
            "created_at": now
        }
        
        await db.tenants.insert_one(tenant)
        tenant.pop("_id", None)
        
        logger.info(f"Tenant created: {tenant_id}")
        return tenant
    
    async def get_tenant(self, tenant_id: str) -> Optional[Dict]:
        """Get tenant by ID"""
        db = get_database()
        return await db.tenants.find_one({"tenant_id": tenant_id}, {"_id": 0})
    
    async def get_all_tenants(self) -> List[Dict]:
        """Get all tenants"""
        db = get_database()
        return await db.tenants.find({}, {"_id": 0}).to_list(100)
    
    # ==================== Tenant User Management ====================
    
    async def create_tenant_user(
        self,
        tenant_id: str,
        email: str,
        password: str,
        name: str,
        role: str = "tenant_admin"
    ) -> Dict:
        """Create a tenant admin user"""
        db = get_database()
        
        # Check if email exists
        existing = await db.tenant_users.find_one({"email": email.lower()}, {"_id": 0})
        if existing:
            raise ValueError("Email already exists")
        
        user_id = f"tadmin_{uuid4().hex[:12]}"
        now = datetime.now(timezone.utc).isoformat()
        
        # Hash password
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        user = {
            "user_id": user_id,
            "tenant_id": tenant_id,
            "email": email.lower(),
            "password_hash": password_hash,
            "name": name,
            "role": role,
            "status": "active",
            "last_login": None,
            "created_at": now
        }
        
        await db.tenant_users.insert_one(user)
        user.pop("_id", None)
        user.pop("password_hash", None)  # Never return password hash
        
        logger.info(f"Tenant user created: {user_id} ({email})")
        return user
    
    async def authenticate_tenant_user(self, email: str, password: str) -> Tuple[bool, Optional[Dict], str]:
        """Authenticate a tenant admin user"""
        db = get_database()
        
        user = await db.tenant_users.find_one({"email": email.lower()}, {"_id": 0})
        if not user:
            return False, None, "Invalid credentials"
        
        # Check status
        if user.get("status") != "active":
            return False, None, "Account is suspended"
        
        # Verify password
        if not bcrypt.checkpw(password.encode('utf-8'), user["password_hash"].encode('utf-8')):
            return False, None, "Invalid credentials"
        
        # Update last login
        await db.tenant_users.update_one(
            {"user_id": user["user_id"]},
            {"$set": {"last_login": datetime.now(timezone.utc).isoformat()}}
        )
        
        user.pop("password_hash", None)
        logger.info(f"Tenant user authenticated: {user['email']}")
        return True, user, "Login successful"
    
    # ==================== Organization Management ====================
    
    async def get_all_organizations(self, tenant_id: str) -> List[Dict]:
        """Get all organizations for a tenant"""
        db = get_database()
        
        # Get orgs with tenant_id OR without tenant_id (for backward compatibility)
        orgs = await db.organizations.find(
            {"$or": [{"tenant_id": tenant_id}, {"tenant_id": {"$exists": False}}]},
            {"_id": 0}
        ).to_list(1000)
        
        # Update orgs without tenant_id
        for org in orgs:
            if not org.get("tenant_id"):
                await db.organizations.update_one(
                    {"org_id": org["org_id"]},
                    {"$set": {"tenant_id": tenant_id, "status": org.get("status", "active")}}
                )
                org["tenant_id"] = tenant_id
        
        # Get owner info for all orgs
        owner_ids = [org.get("owner_id") for org in orgs if org.get("owner_id")]
        owner_map = {}
        if owner_ids:
            owners = await db.users.find(
                {"user_id": {"$in": owner_ids}},
                {"_id": 0, "user_id": 1, "name": 1, "email": 1}
            ).to_list(len(owner_ids))
            owner_map = {o["user_id"]: {"name": o["name"], "email": o["email"]} for o in owners}
        
        # Get stats for each org
        for org in orgs:
            # Get owner info
            owner_info = owner_map.get(org.get("owner_id"))
            if owner_info:
                org["owner_name"] = owner_info["name"]
                org["owner_email"] = owner_info["email"]
            else:
                # Fallback: get first admin
                admin = await db.org_memberships.find_one(
                    {"org_id": org["org_id"], "role": {"$in": ["super_admin", "org_admin"]}},
                    {"_id": 0, "user_id": 1}
                )
                if admin:
                    admin_user = await db.users.find_one(
                        {"user_id": admin["user_id"]},
                        {"_id": 0, "name": 1, "email": 1}
                    )
                    org["owner_name"] = admin_user["name"] if admin_user else "Unknown"
                    org["owner_email"] = admin_user["email"] if admin_user else "Unknown"
                else:
                    org["owner_name"] = "Unknown"
                    org["owner_email"] = "Unknown"
            
            # Count members
            members_count = await db.org_memberships.count_documents({"org_id": org["org_id"]})
            org["total_members"] = members_count
            
            # Count projects
            projects_count = await db.projects.count_documents({"org_id": org["org_id"]})
            org["total_projects"] = projects_count
            
            # Count tasks
            tasks_count = await db.tasks.count_documents({"org_id": org["org_id"]})
            org["total_tasks"] = tasks_count
        
        return orgs
    
    async def get_organization_detail(self, org_id: str) -> Optional[Dict]:
        """Get detailed organization info for tenant admin"""
        db = get_database()
        
        org = await db.organizations.find_one({"org_id": org_id}, {"_id": 0})
        if not org:
            return None
        
        # Get owner info - first try by owner_id, then by created_by email
        owner = None
        if org.get("owner_id"):
            owner = await db.users.find_one(
                {"user_id": org["owner_id"]},
                {"_id": 0, "name": 1, "email": 1}
            )
        
        # If no owner found, try to find by created_by or first admin
        if not owner:
            # Get first org admin or super admin
            admin_membership = await db.org_memberships.find_one(
                {"org_id": org_id, "role": {"$in": ["super_admin", "org_admin"]}},
                {"_id": 0, "user_id": 1}
            )
            if admin_membership:
                owner = await db.users.find_one(
                    {"user_id": admin_membership["user_id"]},
                    {"_id": 0, "name": 1, "email": 1}
                )
        
        org["owner_name"] = owner["name"] if owner else "Unknown"
        org["owner_email"] = owner["email"] if owner else "Unknown"
        
        # Get counts
        org["total_members"] = await db.org_memberships.count_documents({"org_id": org_id})
        org["total_projects"] = await db.projects.count_documents({"org_id": org_id})
        org["total_tasks"] = await db.tasks.count_documents({"org_id": org_id})
        
        return org
    
    async def suspend_organization(
        self,
        org_id: str,
        suspended_by: str,
        reason: Optional[str] = None,
        ip_address: Optional[str] = None
    ) -> Tuple[bool, str]:
        """Suspend an organization"""
        db = get_database()
        
        org = await db.organizations.find_one({"org_id": org_id}, {"_id": 0})
        if not org:
            return False, "Organization not found"
        
        if org.get("status") == "suspended":
            return False, "Organization is already suspended"
        
        now = datetime.now(timezone.utc).isoformat()
        
        # Update organization status
        await db.organizations.update_one(
            {"org_id": org_id},
            {"$set": {
                "status": "suspended",
                "suspended_at": now,
                "suspended_by": suspended_by,
                "suspension_reason": reason
            }}
        )
        
        # Audit log
        await audit_service.log(
            org_id=org_id,
            user_id=suspended_by,
            action="organization.suspend",
            resource_type="organization",
            resource_id=org_id,
            details={
                "reason": reason,
                "ip_address": ip_address,
                "actor_type": "tenant_admin"
            }
        )
        
        # TODO: Force logout all organization users (invalidate sessions)
        
        logger.info(f"Organization {org_id} suspended by {suspended_by}")
        return True, "Organization suspended successfully"

    
    async def delete_organization(
        self,
        org_id: str,
        deleted_by: str,
        ip_address: Optional[str] = None
    ) -> Tuple[bool, str]:
        """Permanently delete an organization and all its data"""
        db = get_database()
        
        org = await db.organizations.find_one({"org_id": org_id}, {"_id": 0})
        if not org:
            return False, "Organization not found"
        
        # Get counts for audit
        projects_count = await db.projects.count_documents({"org_id": org_id})
        tasks_count = await db.tasks.count_documents({"org_id": org_id})
        members_count = await db.org_memberships.count_documents({"org_id": org_id})
        
        # Delete all related data
        await db.projects.delete_many({"org_id": org_id})
        await db.tasks.delete_many({"org_id": org_id})
        await db.time_entries.delete_many({"org_id": org_id})
        await db.comments.delete_many({"org_id": org_id})
        await db.project_budgets.delete_many({"org_id": org_id})
        await db.budget_transactions.delete_many({"org_id": org_id})
        await db.expenses.delete_many({"org_id": org_id})
        await db.org_memberships.delete_many({"org_id": org_id})
        await db.documents.delete_many({"org_id": org_id})
        await db.automations.delete_many({"org_id": org_id})
        await db.workflows.delete_many({"org_id": org_id})
        
        # Delete organization
        await db.organizations.delete_one({"org_id": org_id})
        
        # Audit log
        await audit_service.log(
            org_id=org_id,
            user_id=deleted_by,
            action="organization.delete",
            resource_type="organization",
            resource_id=org_id,
            details={
                "org_name": org["name"],
                "projects_deleted": projects_count,
                "tasks_deleted": tasks_count,
                "members_removed": members_count,
                "ip_address": ip_address,
                "actor_type": "tenant_admin"
            }
        )
        
        logger.warning(f"Organization {org_id} ({org['name']}) DELETED by tenant admin {deleted_by} - {projects_count} projects, {tasks_count} tasks removed")
        return True, f"Organization and all data deleted successfully. {projects_count} projects and {tasks_count} tasks removed."
    
    async def delete_user(
        self,
        user_id: str,
        deleted_by: str,
        ip_address: Optional[str] = None
    ) -> Tuple[bool, str]:
        """Delete a user from the system"""
        db = get_database()
        
        user = await db.users.find_one({"user_id": user_id}, {"_id": 0})
        if not user:
            return False, "User not found"
        
        # Get membership for audit
        membership = await db.org_memberships.find_one({"user_id": user_id}, {"_id": 0})
        org_id = membership["org_id"] if membership else None
        
        # Remove from organization
        if membership:
            await db.org_memberships.delete_one({"user_id": user_id})
        
        # Delete user
        await db.users.delete_one({"user_id": user_id})
        
        # Delete user's data
        await db.time_entries.delete_many({"user_id": user_id})
        await db.comments.delete_many({"user_id": user_id})
        
        # Audit log
        if org_id:
            await audit_service.log(
                org_id=org_id,
                user_id=deleted_by,
                action="user.delete",
                resource_type="user",
                resource_id=user_id,
                details={
                    "user_email": user["email"],
                    "user_name": user["name"],
                    "ip_address": ip_address,
                    "actor_type": "tenant_admin"
                }
            )
        
        logger.warning(f"User {user_id} ({user['email']}) DELETED by tenant admin {deleted_by}")
        return True, "User deleted successfully"
    
    async def activate_organization(
        self,
        org_id: str,
        activated_by: str,
        ip_address: Optional[str] = None
    ) -> Tuple[bool, str]:
        """Activate a suspended organization"""
        db = get_database()
        
        org = await db.organizations.find_one({"org_id": org_id}, {"_id": 0})
        if not org:
            return False, "Organization not found"
        
        if org.get("status") != "suspended":
            return False, "Organization is not suspended"
        
        # Update organization status
        await db.organizations.update_one(
            {"org_id": org_id},
            {"$set": {
                "status": "active",
                "suspended_at": None,
                "suspended_by": None,
                "suspension_reason": None,
                "activated_at": datetime.now(timezone.utc).isoformat(),
                "activated_by": activated_by
            }}
        )
        
        # Audit log
        await audit_service.log(
            org_id=org_id,
            user_id=activated_by,
            action="organization.activate",
            resource_type="organization",
            resource_id=org_id,
            details={
                "ip_address": ip_address,
                "actor_type": "tenant_admin"
            }
        )
        
        logger.info(f"Organization {org_id} activated by {activated_by}")
        return True, "Organization activated successfully"
    
    # ==================== User Management ====================
    
    async def get_organization_users(self, org_id: str) -> List[Dict]:
        """Get all users in an organization for tenant admin view"""
        db = get_database()
        
        # Get memberships
        memberships = await db.org_memberships.find(
            {"org_id": org_id},
            {"_id": 0}
        ).to_list(1000)
        
        user_ids = [m["user_id"] for m in memberships]
        if not user_ids:
            return []
        
        # Get user details
        users = await db.users.find(
            {"user_id": {"$in": user_ids}},
            {"_id": 0}
        ).to_list(len(user_ids))
        
        # Get org info
        org = await db.organizations.find_one({"org_id": org_id}, {"_id": 0, "name": 1})
        org_name = org["name"] if org else "Unknown"
        
        # Merge data
        membership_map = {m["user_id"]: m for m in memberships}
        
        result = []
        for user in users:
            membership = membership_map.get(user["user_id"], {})
            result.append({
                "user_id": user["user_id"],
                "email": user["email"],
                "name": user["name"],
                "org_id": org_id,
                "org_name": org_name,
                "role": membership.get("role", "unknown"),
                "status": user.get("status", "active"),
                "last_login": user.get("last_login"),
                "created_at": user.get("created_at"),
                "suspended_at": user.get("suspended_at"),
                "suspended_by": user.get("suspended_by")
            })
        
        return result
    
    async def suspend_user(
        self,
        user_id: str,
        suspended_by: str,
        reason: Optional[str] = None,
        ip_address: Optional[str] = None
    ) -> Tuple[bool, str]:
        """Suspend a user (tenant admin action)"""
        db = get_database()
        
        user = await db.users.find_one({"user_id": user_id}, {"_id": 0})
        if not user:
            return False, "User not found"
        
        if user.get("status") == "suspended":
            return False, "User is already suspended"
        
        now = datetime.now(timezone.utc).isoformat()
        
        # Update user status
        await db.users.update_one(
            {"user_id": user_id},
            {"$set": {
                "status": "suspended",
                "suspended": True,  # Backward compatibility
                "suspended_at": now,
                "suspended_by": suspended_by,
                "suspension_reason": reason
            }}
        )
        
        # Get org for audit
        membership = await db.org_memberships.find_one({"user_id": user_id}, {"_id": 0, "org_id": 1})
        org_id = membership["org_id"] if membership else None
        
        # Audit log
        if org_id:
            await audit_service.log(
                org_id=org_id,
                user_id=suspended_by,
                action="user.suspend",
                resource_type="user",
                resource_id=user_id,
                details={
                    "reason": reason,
                    "ip_address": ip_address,
                    "actor_type": "tenant_admin",
                    "target_user": user["email"]
                }
            )
        
        # TODO: Invalidate user sessions / force logout
        
        logger.info(f"User {user_id} ({user['email']}) suspended by tenant admin {suspended_by}")
        return True, "User suspended successfully"
    
    async def activate_user(
        self,
        user_id: str,
        activated_by: str,
        ip_address: Optional[str] = None
    ) -> Tuple[bool, str]:
        """Activate a suspended user"""
        db = get_database()
        
        user = await db.users.find_one({"user_id": user_id}, {"_id": 0})
        if not user:
            return False, "User not found"
        
        if user.get("status") != "suspended":
            return False, "User is not suspended"
        
        # Update user status
        await db.users.update_one(
            {"user_id": user_id},
            {"$set": {
                "status": "active",
                "suspended": False,
                "suspended_at": None,
                "suspended_by": None,
                "suspension_reason": None,
                "activated_at": datetime.now(timezone.utc).isoformat(),
                "activated_by": activated_by
            }}
        )
        
        # Get org for audit
        membership = await db.org_memberships.find_one({"user_id": user_id}, {"_id": 0, "org_id": 1})
        org_id = membership["org_id"] if membership else None
        
        # Audit log
        if org_id:
            await audit_service.log(
                org_id=org_id,
                user_id=activated_by,
                action="user.activate",
                resource_type="user",
                resource_id=user_id,
                details={
                    "ip_address": ip_address,
                    "actor_type": "tenant_admin",
                    "target_user": user["email"]
                }
            )
        
        logger.info(f"User {user_id} ({user['email']}) activated by tenant admin {activated_by}")
        return True, "User activated successfully"
    
    # ==================== Seeding ====================
    
    async def seed_initial_data(self) -> Dict:
        """Seed initial tenant and tenant super admin"""
        db = get_database()
        
        # Check if tenant exists
        existing_tenant = await db.tenants.find_one({}, {"_id": 0})
        if existing_tenant:
            logger.info("Tenant already exists, skipping seed")
            return {"message": "Tenant already exists", "tenant_id": existing_tenant["tenant_id"]}
        
        # Create default tenant
        tenant = await self.create_tenant(name="ProFlow Tenant", domain=None)
        
        # Create tenant super admin
        admin = await self.create_tenant_user(
            tenant_id=tenant["tenant_id"],
            email="mahmoud@mahmoud.com",
            password="Su@12345",
            name="Mahmoud - Tenant Super Admin",
            role="tenant_super_admin"
        )
        
        # Update all existing organizations to belong to this tenant
        await db.organizations.update_many(
            {"tenant_id": {"$exists": False}},
            {"$set": {"tenant_id": tenant["tenant_id"], "status": "active"}}
        )
        
        logger.info(f"Seeded tenant {tenant['tenant_id']} with super admin {admin['user_id']}")
        return {
            "message": "Initial tenant and super admin created successfully",
            "tenant_id": tenant["tenant_id"],
            "admin_email": "mahmoud@mahmoud.com",
            "admin_user_id": admin["user_id"]
        }


# Singleton instance
tenant_service = TenantService()
