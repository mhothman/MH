"""Automation Repository - Data access layer for automations"""
from typing import Dict, List, Optional
from datetime import datetime, timezone
import uuid

from core.database import get_database
from repositories import BaseRepository


class AutomationRepository(BaseRepository):
    """Repository for automation data access"""
    
    @property
    def collection_name(self) -> str:
        return "automations"
    
    @property
    def id_field(self) -> str:
        return "automation_id"
    
    async def find_by_id(self, automation_id: str) -> Optional[Dict]:
        """Find automation by ID"""
        db = get_database()
        return await db.automations.find_one({self.id_field: automation_id}, {"_id": 0})
    
    async def find_all(self, query: Dict = None, limit: int = 100) -> List[Dict]:
        """Find all automations matching query"""
        db = get_database()
        return await db.automations.find(query or {}, {"_id": 0}).to_list(limit)
    
    async def find_by_org(self, org_id: str, enabled_only: bool = False) -> List[Dict]:
        """Find automations by organization"""
        db = get_database()
        query = {"org_id": org_id}
        if enabled_only:
            query["enabled"] = True
        return await db.automations.find(query, {"_id": 0}).sort("created_at", -1).to_list(100)
    
    async def find_by_trigger(self, org_id: str, trigger_type: str, enabled_only: bool = True) -> List[Dict]:
        """Find automations by trigger type"""
        db = get_database()
        query = {"org_id": org_id, "trigger_type": trigger_type}
        if enabled_only:
            query["enabled"] = True
        return await db.automations.find(query, {"_id": 0}).to_list(100)
    
    async def create(self, data: Dict) -> Dict:
        """Create a new automation"""
        db = get_database()
        automation_id = f"auto_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc).isoformat()
        
        automation = {
            "automation_id": automation_id,
            **data,
            "enabled": data.get("enabled", True),
            "execution_count": 0,
            "created_at": now,
            "updated_at": now
        }
        
        await db.automations.insert_one(automation)
        automation.pop("_id", None)
        return automation
    
    async def update(self, automation_id: str, data: Dict) -> bool:
        """Update an automation"""
        db = get_database()
        data["updated_at"] = datetime.now(timezone.utc).isoformat()
        result = await db.automations.update_one(
            {self.id_field: automation_id},
            {"$set": data}
        )
        return result.modified_count > 0
    
    async def delete(self, automation_id: str) -> bool:
        """Delete an automation"""
        db = get_database()
        result = await db.automations.delete_one({self.id_field: automation_id})
        return result.deleted_count > 0
    
    async def increment_execution_count(self, automation_id: str) -> bool:
        """Increment execution count for an automation"""
        db = get_database()
        now = datetime.now(timezone.utc).isoformat()
        result = await db.automations.update_one(
            {self.id_field: automation_id},
            {
                "$inc": {"execution_count": 1},
                "$set": {"last_executed_at": now}
            }
        )
        return result.modified_count > 0
    
    async def toggle_enabled(self, automation_id: str, enabled: bool) -> bool:
        """Toggle automation enabled status"""
        return await self.update(automation_id, {"enabled": enabled})
    
    async def add_execution_history(self, automation_id: str, execution: Dict) -> bool:
        """Add execution history record"""
        db = get_database()
        execution_id = f"exec_{uuid.uuid4().hex[:8]}"
        now = datetime.now(timezone.utc).isoformat()
        
        history_entry = {
            "execution_id": execution_id,
            "automation_id": automation_id,
            "executed_at": now,
            **execution
        }
        
        await db.automation_history.insert_one(history_entry)
        return True
    
    async def get_execution_history(self, automation_id: str, limit: int = 50) -> List[Dict]:
        """Get execution history for an automation"""
        db = get_database()
        return await db.automation_history.find(
            {"automation_id": automation_id},
            {"_id": 0}
        ).sort("executed_at", -1).to_list(limit)
    
    async def count_by_org(self, org_id: str) -> int:
        """Count automations in an organization"""
        db = get_database()
        return await db.automations.count_documents({"org_id": org_id})


# Singleton instance
automation_repository = AutomationRepository()
