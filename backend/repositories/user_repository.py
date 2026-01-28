"""User Repository - Data access layer for users"""
from typing import Dict, List, Optional
from datetime import datetime, timezone
import uuid

from core.database import get_database
from repositories import BaseRepository


class UserRepository(BaseRepository):
    """Repository for user data access"""
    
    @property
    def collection_name(self) -> str:
        return "users"
    
    @property
    def id_field(self) -> str:
        return "user_id"
    
    async def find_by_id(self, user_id: str) -> Optional[Dict]:
        """Find user by ID (excludes password)"""
        db = get_database()
        return await db.users.find_one({self.id_field: user_id}, {"_id": 0, "password_hash": 0})
    
    async def find_by_email(self, email: str) -> Optional[Dict]:
        """Find user by email"""
        db = get_database()
        return await db.users.find_one({"email": email.lower()}, {"_id": 0})
    
    async def find_all(self, query: Dict = None, limit: int = 100) -> List[Dict]:
        """Find all users matching query"""
        db = get_database()
        return await db.users.find(query or {}, {"_id": 0, "password_hash": 0}).to_list(limit)
    
    async def find_by_ids(self, user_ids: List[str]) -> List[Dict]:
        """Find multiple users by IDs"""
        db = get_database()
        return await db.users.find(
            {self.id_field: {"$in": user_ids}},
            {"_id": 0, "password_hash": 0}
        ).to_list(len(user_ids))
    
    async def get_user_map(self, user_ids: List[str]) -> Dict[str, Dict]:
        """Get a map of user_id -> user data"""
        users = await self.find_by_ids(user_ids)
        return {u["user_id"]: u for u in users}
    
    async def create(self, data: Dict) -> Dict:
        """Create a new user"""
        db = get_database()
        user_id = f"user_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc).isoformat()
        
        user = {
            "user_id": user_id,
            **data,
            "created_at": now
        }
        
        await db.users.insert_one(user)
        user.pop("_id", None)
        user.pop("password_hash", None)
        return user
    
    async def update(self, user_id: str, data: Dict) -> bool:
        """Update a user"""
        db = get_database()
        result = await db.users.update_one(
            {self.id_field: user_id},
            {"$set": data}
        )
        return result.modified_count > 0
    
    async def delete(self, user_id: str) -> bool:
        """Delete a user"""
        db = get_database()
        result = await db.users.delete_one({self.id_field: user_id})
        return result.deleted_count > 0
    
    async def get_org_members(self, org_id: str) -> List[Dict]:
        """Get all members of an organization with user details"""
        db = get_database()
        return await db.org_memberships.aggregate([
            {"$match": {"org_id": org_id}},
            {"$lookup": {
                "from": "users",
                "localField": "user_id",
                "foreignField": "user_id",
                "as": "user"
            }},
            {"$unwind": "$user"},
            {"$project": {
                "_id": 0,
                "user_id": "$user.user_id",
                "name": {"$ifNull": ["$user.name", "Unknown"]},
                "email": {"$ifNull": ["$user.email", ""]},
                "picture": "$user.picture",
                "role": "$role"
            }}
        ]).to_list(100)


# Singleton instance
user_repository = UserRepository()
