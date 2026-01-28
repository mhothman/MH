"""Task Repository - Data access layer for tasks"""
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
import uuid

from core.database import get_database
from repositories import BaseRepository


class TaskRepository(BaseRepository):
    """Repository for task data access"""
    
    @property
    def collection_name(self) -> str:
        return "tasks"
    
    @property
    def id_field(self) -> str:
        return "task_id"
    
    async def find_by_id(self, task_id: str) -> Optional[Dict]:
        """Find task by ID"""
        db = get_database()
        return await db.tasks.find_one({self.id_field: task_id}, {"_id": 0})
    
    async def find_all(self, query: Dict = None, limit: int = 500) -> List[Dict]:
        """Find all tasks matching query"""
        db = get_database()
        return await db.tasks.find(query or {}, {"_id": 0}).to_list(limit)
    
    async def find_by_project(self, project_id: str, status: str = None, assignee_id: str = None) -> List[Dict]:
        """Find tasks by project with optional filters"""
        db = get_database()
        query = {"project_id": project_id}
        if status:
            query["status"] = status
        if assignee_id:
            query["assignee_ids"] = assignee_id
        return await db.tasks.find(query, {"_id": 0}).to_list(500)
    
    async def find_by_assignee(self, user_id: str, status: str = None) -> List[Dict]:
        """Find tasks assigned to user"""
        db = get_database()
        query = {"assignee_ids": user_id}
        if status:
            query["status"] = status
        return await db.tasks.find(query, {"_id": 0}).to_list(500)
    
    async def find_overdue(self, project_ids: List[str]) -> List[Dict]:
        """Find overdue tasks"""
        db = get_database()
        now = datetime.now(timezone.utc).isoformat()
        return await db.tasks.find({
            "project_id": {"$in": project_ids},
            "due_date": {"$lt": now},
            "status": {"$ne": "done"}
        }, {"_id": 0}).to_list(500)
    
    async def create(self, data: Dict) -> Dict:
        """Create a new task"""
        db = get_database()
        task_id = f"task_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc).isoformat()
        
        task = {
            "task_id": task_id,
            **data,
            "created_at": now,
            "updated_at": now
        }
        
        await db.tasks.insert_one(task)
        task.pop("_id", None)
        return task
    
    async def update(self, task_id: str, data: Dict) -> bool:
        """Update a task"""
        db = get_database()
        data["updated_at"] = datetime.now(timezone.utc).isoformat()
        result = await db.tasks.update_one(
            {self.id_field: task_id},
            {"$set": data}
        )
        return result.modified_count > 0
    
    async def delete(self, task_id: str) -> bool:
        """Delete a task"""
        db = get_database()
        result = await db.tasks.delete_one({self.id_field: task_id})
        return result.deleted_count > 0
    
    async def count_by_project(self, project_id: str) -> Dict[str, int]:
        """Get task counts by status for a project"""
        db = get_database()
        stats = await db.tasks.aggregate([
            {"$match": {"project_id": project_id}},
            {"$group": {
                "_id": None,
                "total": {"$sum": 1},
                "completed": {"$sum": {"$cond": [{"$eq": ["$status", "done"]}, 1, 0]}},
                "in_progress": {"$sum": {"$cond": [{"$eq": ["$status", "in_progress"]}, 1, 0]}},
                "todo": {"$sum": {"$cond": [{"$eq": ["$status", "todo"]}, 1, 0]}}
            }}
        ]).to_list(1)
        
        return stats[0] if stats else {"total": 0, "completed": 0, "in_progress": 0, "todo": 0}
    
    async def bulk_count_by_projects(self, project_ids: List[str]) -> Dict[str, Dict[str, int]]:
        """Get task counts for multiple projects in one query"""
        db = get_database()
        stats = await db.tasks.aggregate([
            {"$match": {"project_id": {"$in": project_ids}}},
            {"$group": {
                "_id": "$project_id",
                "total": {"$sum": 1},
                "completed": {"$sum": {"$cond": [{"$eq": ["$status", "done"]}, 1, 0]}}
            }}
        ]).to_list(len(project_ids))
        
        return {s["_id"]: {"total": s["total"], "completed": s["completed"]} for s in stats}


# Singleton instance
task_repository = TaskRepository()
