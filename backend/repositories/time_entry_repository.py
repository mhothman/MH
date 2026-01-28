"""Time Entry Repository - Data access layer for time entries"""
from typing import Dict, List, Optional
from datetime import datetime, timezone
import uuid

from core.database import get_database
from repositories import BaseRepository


class TimeEntryRepository(BaseRepository):
    """Repository for time entry data access"""
    
    @property
    def collection_name(self) -> str:
        return "time_entries"
    
    @property
    def id_field(self) -> str:
        return "entry_id"
    
    async def find_by_id(self, entry_id: str) -> Optional[Dict]:
        """Find time entry by ID"""
        db = get_database()
        return await db.time_entries.find_one({self.id_field: entry_id}, {"_id": 0})
    
    async def find_all(self, query: Dict = None, limit: int = 500) -> List[Dict]:
        """Find all time entries matching query"""
        db = get_database()
        return await db.time_entries.find(query or {}, {"_id": 0}).sort("start_time", -1).to_list(limit)
    
    async def find_by_user(self, user_id: str, start_date: str = None, end_date: str = None) -> List[Dict]:
        """Find time entries by user with optional date range"""
        db = get_database()
        query = {"user_id": user_id}
        if start_date:
            query["start_time"] = {"$gte": start_date}
        if end_date:
            if "start_time" in query:
                query["start_time"]["$lte"] = end_date
            else:
                query["start_time"] = {"$lte": end_date}
        return await db.time_entries.find(query, {"_id": 0}).sort("start_time", -1).to_list(500)
    
    async def find_by_task(self, task_id: str) -> List[Dict]:
        """Find time entries by task"""
        db = get_database()
        return await db.time_entries.find({"task_id": task_id}, {"_id": 0}).sort("start_time", -1).to_list(500)
    
    async def find_active_timer(self, user_id: str) -> Optional[Dict]:
        """Find user's active timer"""
        db = get_database()
        return await db.time_entries.find_one(
            {"user_id": user_id, "end_time": None},
            {"_id": 0}
        )
    
    async def create(self, data: Dict) -> Dict:
        """Create a new time entry"""
        db = get_database()
        entry_id = f"time_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc).isoformat()
        
        entry = {
            "entry_id": entry_id,
            **data,
            "created_at": now
        }
        
        await db.time_entries.insert_one(entry)
        entry.pop("_id", None)
        return entry
    
    async def update(self, entry_id: str, data: Dict) -> bool:
        """Update a time entry"""
        db = get_database()
        result = await db.time_entries.update_one(
            {self.id_field: entry_id},
            {"$set": data}
        )
        return result.modified_count > 0
    
    async def delete(self, entry_id: str) -> bool:
        """Delete a time entry"""
        db = get_database()
        result = await db.time_entries.delete_one({self.id_field: entry_id})
        return result.deleted_count > 0
    
    async def stop_active_timer(self, user_id: str) -> Optional[Dict]:
        """Stop user's active timer and return the entry"""
        db = get_database()
        active = await self.find_active_timer(user_id)
        if not active:
            return None
        
        now = datetime.now(timezone.utc)
        start = datetime.fromisoformat(active["start_time"].replace("Z", "+00:00"))
        duration_minutes = int((now - start).total_seconds() / 60)
        
        await db.time_entries.update_one(
            {"entry_id": active["entry_id"]},
            {"$set": {"end_time": now.isoformat(), "duration_minutes": duration_minutes}}
        )
        
        return await self.find_by_id(active["entry_id"])
    
    async def get_total_hours_by_task(self, task_id: str) -> float:
        """Get total hours logged for a task"""
        db = get_database()
        result = await db.time_entries.aggregate([
            {"$match": {"task_id": task_id}},
            {"$group": {"_id": None, "total_minutes": {"$sum": "$duration_minutes"}}}
        ]).to_list(1)
        
        return result[0]["total_minutes"] / 60 if result else 0
    
    async def get_summary_by_user(self, user_ids: List[str], start_date: str, end_date: str) -> List[Dict]:
        """Get time summary grouped by user"""
        db = get_database()
        return await db.time_entries.aggregate([
            {"$match": {
                "user_id": {"$in": user_ids},
                "start_time": {"$gte": start_date, "$lte": end_date}
            }},
            {"$group": {
                "_id": "$user_id",
                "total_minutes": {"$sum": "$duration_minutes"},
                "entry_count": {"$sum": 1}
            }}
        ]).to_list(len(user_ids))


# Singleton instance
time_entry_repository = TimeEntryRepository()
