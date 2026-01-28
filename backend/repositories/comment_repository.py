"""Comment Repository - Data access layer for comments"""
from typing import Dict, List, Optional
from datetime import datetime, timezone
import uuid

from core.database import get_database
from repositories import BaseRepository


class CommentRepository(BaseRepository):
    """Repository for comment data access"""
    
    @property
    def collection_name(self) -> str:
        return "comments"
    
    @property
    def id_field(self) -> str:
        return "comment_id"
    
    async def find_by_id(self, comment_id: str) -> Optional[Dict]:
        """Find comment by ID"""
        db = get_database()
        return await db.comments.find_one({self.id_field: comment_id}, {"_id": 0})
    
    async def find_all(self, query: Dict = None, limit: int = 100) -> List[Dict]:
        """Find all comments matching query"""
        db = get_database()
        return await db.comments.find(query or {}, {"_id": 0}).sort("created_at", -1).to_list(limit)
    
    async def find_by_task(self, task_id: str, limit: int = 100) -> List[Dict]:
        """Find comments by task"""
        db = get_database()
        return await db.comments.find({"task_id": task_id}, {"_id": 0}).sort("created_at", -1).to_list(limit)
    
    async def find_by_project(self, project_id: str, limit: int = 500) -> List[Dict]:
        """Find comments by project"""
        db = get_database()
        return await db.comments.find({"project_id": project_id}, {"_id": 0}).sort("created_at", -1).to_list(limit)
    
    async def find_by_user(self, user_id: str, limit: int = 100) -> List[Dict]:
        """Find comments by user"""
        db = get_database()
        return await db.comments.find({"author_id": user_id}, {"_id": 0}).sort("created_at", -1).to_list(limit)
    
    async def create(self, data: Dict) -> Dict:
        """Create a new comment"""
        db = get_database()
        comment_id = f"cmt_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc).isoformat()
        
        comment = {
            "comment_id": comment_id,
            **data,
            "created_at": now,
            "updated_at": now
        }
        
        await db.comments.insert_one(comment)
        comment.pop("_id", None)
        return comment
    
    async def update(self, comment_id: str, data: Dict) -> bool:
        """Update a comment"""
        db = get_database()
        data["updated_at"] = datetime.now(timezone.utc).isoformat()
        result = await db.comments.update_one(
            {self.id_field: comment_id},
            {"$set": data}
        )
        return result.modified_count > 0
    
    async def delete(self, comment_id: str) -> bool:
        """Delete a comment"""
        db = get_database()
        result = await db.comments.delete_one({self.id_field: comment_id})
        return result.deleted_count > 0
    
    async def delete_by_task(self, task_id: str) -> int:
        """Delete all comments for a task"""
        db = get_database()
        result = await db.comments.delete_many({"task_id": task_id})
        return result.deleted_count
    
    async def count_by_task(self, task_id: str) -> int:
        """Count comments for a task"""
        db = get_database()
        return await db.comments.count_documents({"task_id": task_id})
    
    async def find_mentions(self, user_id: str, limit: int = 50) -> List[Dict]:
        """Find comments where user is mentioned"""
        db = get_database()
        return await db.comments.find(
            {"mentions": user_id},
            {"_id": 0}
        ).sort("created_at", -1).to_list(limit)


# Singleton instance
comment_repository = CommentRepository()
