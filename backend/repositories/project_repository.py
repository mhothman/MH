"""Project Repository - Data access layer for projects"""
from typing import Dict, List, Optional
from datetime import datetime, timezone
import uuid

from core.database import get_database
from repositories import BaseRepository


class ProjectRepository(BaseRepository):
    """Repository for project data access"""
    
    @property
    def collection_name(self) -> str:
        return "projects"
    
    @property
    def id_field(self) -> str:
        return "project_id"
    
    async def find_by_id(self, project_id: str) -> Optional[Dict]:
        """Find project by ID"""
        db = get_database()
        return await db.projects.find_one({self.id_field: project_id}, {"_id": 0})
    
    async def find_all(self, query: Dict = None, limit: int = 500) -> List[Dict]:
        """Find all projects matching query"""
        db = get_database()
        return await db.projects.find(query or {}, {"_id": 0}).to_list(limit)
    
    async def find_by_org(self, org_id: str, status: str = None) -> List[Dict]:
        """Find projects by organization"""
        db = get_database()
        query = {"org_id": org_id}
        if status:
            query["status"] = status
        return await db.projects.find(query, {"_id": 0}).sort("created_at", -1).to_list(500)
    
    async def find_by_customer(self, customer_id: str) -> List[Dict]:
        """Find projects by customer"""
        db = get_database()
        return await db.projects.find({"customer_id": customer_id}, {"_id": 0}).to_list(100)
    
    async def create(self, data: Dict) -> Dict:
        """Create a new project"""
        db = get_database()
        project_id = f"proj_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc).isoformat()
        
        project = {
            "project_id": project_id,
            **data,
            "created_at": now,
            "updated_at": now
        }
        
        await db.projects.insert_one(project)
        project.pop("_id", None)
        return project
    
    async def update(self, project_id: str, data: Dict) -> bool:
        """Update a project"""
        db = get_database()
        data["updated_at"] = datetime.now(timezone.utc).isoformat()
        result = await db.projects.update_one(
            {self.id_field: project_id},
            {"$set": data}
        )
        return result.modified_count > 0
    
    async def delete(self, project_id: str) -> bool:
        """Delete a project"""
        db = get_database()
        result = await db.projects.delete_one({self.id_field: project_id})
        return result.deleted_count > 0
    
    async def get_project_ids_for_orgs(self, org_ids: List[str]) -> List[str]:
        """Get project IDs for multiple organizations"""
        db = get_database()
        projects = await db.projects.find(
            {"org_id": {"$in": org_ids}},
            {"project_id": 1}
        ).to_list(500)
        return [p["project_id"] for p in projects]
    
    async def count_by_org(self, org_id: str) -> int:
        """Count projects in an organization"""
        db = get_database()
        return await db.projects.count_documents({"org_id": org_id})
    
    async def get_with_task_stats(self, org_id: str) -> List[Dict]:
        """Get projects with task statistics using aggregation"""
        db = get_database()
        
        # Get projects
        projects = await self.find_by_org(org_id)
        if not projects:
            return []
        
        # Get task stats in bulk
        project_ids = [p["project_id"] for p in projects]
        task_stats = await db.tasks.aggregate([
            {"$match": {"project_id": {"$in": project_ids}}},
            {"$group": {
                "_id": "$project_id",
                "total": {"$sum": 1},
                "completed": {"$sum": {"$cond": [{"$eq": ["$status", "done"]}, 1, 0]}}
            }}
        ]).to_list(len(project_ids))
        
        stats_map = {s["_id"]: s for s in task_stats}
        
        # Merge stats into projects
        for project in projects:
            stats = stats_map.get(project["project_id"], {"total": 0, "completed": 0})
            project["task_count"] = stats["total"]
            project["completed_tasks"] = stats["completed"]
        
        return projects


# Singleton instance
project_repository = ProjectRepository()
