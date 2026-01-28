"""Organization Repository - Data access layer for organizations"""
from typing import Dict, List, Optional
from datetime import datetime, timezone
import uuid

from core.database import get_database
from repositories import BaseRepository


class OrganizationRepository(BaseRepository):
    """Repository for organization data access"""
    
    @property
    def collection_name(self) -> str:
        return "organizations"
    
    @property
    def id_field(self) -> str:
        return "org_id"
    
    async def find_by_id(self, org_id: str) -> Optional[Dict]:
        """Find organization by ID"""
        db = get_database()
        return await db.organizations.find_one({self.id_field: org_id}, {"_id": 0})
    
    async def find_all(self, query: Dict = None, limit: int = 100) -> List[Dict]:
        """Find all organizations matching query"""
        db = get_database()
        return await db.organizations.find(query or {}, {"_id": 0}).to_list(limit)
    
    async def find_by_slug(self, slug: str) -> Optional[Dict]:
        """Find organization by slug"""
        db = get_database()
        return await db.organizations.find_one({"slug": slug}, {"_id": 0})
    
    async def find_by_domain(self, domain: str) -> Optional[Dict]:
        """Find organization by custom domain"""
        db = get_database()
        return await db.organizations.find_one({"custom_domain": domain}, {"_id": 0})
    
    async def create(self, data: Dict) -> Dict:
        """Create a new organization"""
        db = get_database()
        org_id = f"org_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc).isoformat()
        
        org = {
            "org_id": org_id,
            **data,
            "created_at": now,
            "updated_at": now
        }
        
        await db.organizations.insert_one(org)
        org.pop("_id", None)
        return org
    
    async def update(self, org_id: str, data: Dict) -> bool:
        """Update an organization"""
        db = get_database()
        data["updated_at"] = datetime.now(timezone.utc).isoformat()
        result = await db.organizations.update_one(
            {self.id_field: org_id},
            {"$set": data}
        )
        return result.modified_count > 0
    
    async def delete(self, org_id: str) -> bool:
        """Delete an organization"""
        db = get_database()
        result = await db.organizations.delete_one({self.id_field: org_id})
        return result.deleted_count > 0
    
    async def get_members(self, org_id: str) -> List[Dict]:
        """Get all members of an organization"""
        db = get_database()
        memberships = await db.org_memberships.find({"org_id": org_id}, {"_id": 0}).to_list(200)
        
        if not memberships:
            return []
        
        user_ids = [m["user_id"] for m in memberships]
        users = await db.users.find(
            {"user_id": {"$in": user_ids}},
            {"_id": 0, "user_id": 1, "name": 1, "email": 1, "picture": 1}
        ).to_list(len(user_ids))
        
        user_map = {u["user_id"]: u for u in users}
        
        result = []
        for m in memberships:
            user = user_map.get(m["user_id"], {})
            result.append({
                **user,
                "org_role": m.get("role"),
                "custom_role_id": m.get("custom_role_id"),
                "custom_role_name": m.get("custom_role_name"),
                "suspended": m.get("suspended", False),
                "joined_at": m.get("joined_at")
            })
        
        return result
    
    async def get_member_count(self, org_id: str) -> int:
        """Count members in an organization"""
        db = get_database()
        return await db.org_memberships.count_documents({"org_id": org_id})
    
    async def add_member(self, org_id: str, user_id: str, role: str = "team_member") -> bool:
        """Add a member to an organization"""
        db = get_database()
        now = datetime.now(timezone.utc).isoformat()
        
        # Check if already member
        existing = await db.org_memberships.find_one({"org_id": org_id, "user_id": user_id})
        if existing:
            return False
        
        await db.org_memberships.insert_one({
            "org_id": org_id,
            "user_id": user_id,
            "role": role,
            "joined_at": now
        })
        return True
    
    async def remove_member(self, org_id: str, user_id: str) -> bool:
        """Remove a member from an organization"""
        db = get_database()
        result = await db.org_memberships.delete_one({"org_id": org_id, "user_id": user_id})
        return result.deleted_count > 0
    
    async def update_member_role(self, org_id: str, user_id: str, role: str = None, custom_role_id: str = None, custom_role_name: str = None) -> bool:
        """Update a member's role"""
        db = get_database()
        update_data = {}
        if role:
            update_data["role"] = role
            update_data["custom_role_id"] = None
            update_data["custom_role_name"] = None
        if custom_role_id:
            update_data["custom_role_id"] = custom_role_id
            update_data["custom_role_name"] = custom_role_name
        
        result = await db.org_memberships.update_one(
            {"org_id": org_id, "user_id": user_id},
            {"$set": update_data}
        )
        return result.modified_count > 0
    
    async def get_user_membership(self, user_id: str, org_id: str) -> Optional[Dict]:
        """Get user's membership in an organization"""
        db = get_database()
        return await db.org_memberships.find_one(
            {"org_id": org_id, "user_id": user_id},
            {"_id": 0}
        )
    
    async def get_user_organizations(self, user_id: str) -> List[Dict]:
        """Get all organizations a user belongs to"""
        db = get_database()
        memberships = await db.org_memberships.find({"user_id": user_id}, {"_id": 0}).to_list(50)
        
        if not memberships:
            return []
        
        org_ids = [m["org_id"] for m in memberships]
        orgs = await db.organizations.find(
            {"org_id": {"$in": org_ids}},
            {"_id": 0}
        ).to_list(len(org_ids))
        
        # Merge membership data with org data
        membership_map = {m["org_id"]: m for m in memberships}
        result = []
        for org in orgs:
            m = membership_map.get(org["org_id"], {})
            result.append({
                **org,
                "role": m.get("role"),
                "custom_role_id": m.get("custom_role_id"),
                "custom_role_name": m.get("custom_role_name")
            })
        
        return result


# Singleton instance
organization_repository = OrganizationRepository()
