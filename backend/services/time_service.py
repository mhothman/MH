"""Time Tracking Service - Business logic for time entries and timers"""
from datetime import datetime, timezone
from typing import List, Dict, Optional, Tuple, Any
import uuid
import logging

from core.database import get_database

logger = logging.getLogger(__name__)

# Import budget service for cost tracking (avoid circular import)
def get_budget_service():
    from services.budget_service import budget_service
    return budget_service


class TimeService:
    """Service for time tracking business logic"""
    
    # =============================================
    # Timer Operations
    # =============================================
    
    async def start_timer(
        self,
        user_id: str,
        task_id: str,
        org_id: str,
        description: str = None
    ) -> Tuple[bool, str, Optional[Dict]]:
        """Start a timer for a task"""
        db = get_database()
        
        # Check for existing active timer
        existing = await db.timers.find_one({
            "user_id": user_id,
            "is_running": True
        }, {"_id": 0})
        
        if existing:
            return False, "You already have an active timer. Stop it before starting a new one.", None
        
        timer_id = f"timer_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc)
        
        timer = {
            "timer_id": timer_id,
            "task_id": task_id,
            "user_id": user_id,
            "org_id": org_id,
            "description": description,
            "started_at": now.isoformat(),
            "is_running": True
        }
        
        await db.timers.insert_one(timer)
        timer.pop("_id", None)
        timer["started_at"] = now
        
        return True, "Timer started", timer
    
    async def stop_timer(self, user_id: str) -> Tuple[bool, str, Optional[Dict]]:
        """Stop the active timer and create a time entry"""
        db = get_database()
        
        timer = await db.timers.find_one({
            "user_id": user_id,
            "is_running": True
        }, {"_id": 0})
        
        if not timer:
            return False, "No active timer found", None
        
        # Calculate duration
        started_at = datetime.fromisoformat(timer["started_at"].replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        duration_seconds = (now - started_at).total_seconds()
        duration_minutes = int(duration_seconds / 60)
        
        # Create time entry
        entry_id = f"time_{uuid.uuid4().hex[:12]}"
        entry = {
            "entry_id": entry_id,
            "task_id": timer["task_id"],
            "user_id": user_id,
            "org_id": timer["org_id"],
            "duration_minutes": max(1, duration_minutes),
            "description": timer.get("description"),
            "date": now.strftime("%Y-%m-%d"),
            "created_at": now.isoformat(),
            "from_timer": True
        }
        
        await db.time_entries.insert_one(entry)
        
        # Process budget cost tracking
        try:
            # Get task to find project_id
            task = await db.tasks.find_one({"task_id": timer["task_id"]}, {"_id": 0, "project_id": 1})
            if task:
                budget_service = get_budget_service()
                await budget_service.process_time_entry_cost(
                    org_id=timer["org_id"],
                    project_id=task["project_id"],
                    task_id=timer["task_id"],
                    user_id=user_id,
                    duration_minutes=max(1, duration_minutes),
                    time_entry_id=entry_id
                )
        except Exception as e:
            logger.warning(f"Failed to process budget cost for time entry {entry_id}: {e}")
        
        # Update task's actual hours
        await db.tasks.update_one(
            {"task_id": timer["task_id"]},
            {"$inc": {"actual_hours": duration_minutes / 60}}
        )
        
        # Mark timer as stopped
        await db.timers.update_one(
            {"timer_id": timer["timer_id"]},
            {"$set": {"is_running": False, "stopped_at": now.isoformat()}}
        )
        
        return True, "Timer stopped", {
            "duration_minutes": duration_minutes,
            "entry_id": entry_id
        }
    
    async def get_active_timer(self, user_id: str) -> Optional[Dict]:
        """Get the user's active timer"""
        db = get_database()
        
        timer = await db.timers.find_one({
            "user_id": user_id,
            "is_running": True
        }, {"_id": 0})
        
        if not timer:
            return None
        
        # Calculate elapsed time
        started_at = datetime.fromisoformat(timer["started_at"].replace("Z", "+00:00"))
        elapsed = (datetime.now(timezone.utc) - started_at).total_seconds()
        
        timer["started_at"] = started_at
        timer["elapsed_seconds"] = int(elapsed)
        
        return timer
    
    async def discard_timer(self, user_id: str) -> bool:
        """Discard the active timer without creating a time entry"""
        db = get_database()
        
        result = await db.timers.delete_one({
            "user_id": user_id,
            "is_running": True
        })
        
        return result.deleted_count > 0
    
    # =============================================
    # Time Entry CRUD
    # =============================================
    
    async def get_entries(
        self,
        user_id: str = None,
        task_id: str = None,
        task_ids: List[str] = None,
        start_date: str = None,
        end_date: str = None,
        limit: int = 100
    ) -> List[Dict]:
        """Get time entries with filters"""
        db = get_database()
        
        query = {}
        
        if task_id:
            query["task_id"] = task_id
        elif task_ids:
            query["task_id"] = {"$in": task_ids}
        elif user_id:
            query["user_id"] = user_id
        
        if start_date:
            query["date"] = {"$gte": start_date}
        if end_date:
            if "date" in query:
                query["date"]["$lte"] = end_date
            else:
                query["date"] = {"$lte": end_date}
        
        entries = await db.time_entries.find(query, {"_id": 0}).sort("created_at", -1).limit(limit).to_list(limit)
        
        # Batch fetch user names and pictures
        user_ids = list(set(e.get("user_id") for e in entries if e.get("user_id")))
        if user_ids:
            users = await db.users.find(
                {"user_id": {"$in": user_ids}}, 
                {"_id": 0, "user_id": 1, "name": 1, "picture": 1}
            ).to_list(len(user_ids))
            user_map = {u["user_id"]: {"name": u.get("name", "Unknown"), "picture": u.get("picture")} for u in users}
        else:
            user_map = {}
        
        for entry in entries:
            user_info = user_map.get(entry.get("user_id"), {"name": "Unknown", "picture": None})
            entry["user_name"] = user_info["name"]
            entry["user_picture"] = user_info["picture"]
            if isinstance(entry.get("created_at"), str):
                entry["created_at"] = datetime.fromisoformat(entry["created_at"].replace("Z", "+00:00"))
        
        return entries
    
    async def create_entry(
        self,
        user_id: str,
        task_id: str,
        org_id: str,
        duration_minutes: int,
        description: str = None,
        date: str = None
    ) -> Dict:
        """Create a manual time entry"""
        db = get_database()
        
        entry_id = f"time_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc)
        
        entry = {
            "entry_id": entry_id,
            "task_id": task_id,
            "user_id": user_id,
            "org_id": org_id,
            "duration_minutes": duration_minutes,
            "description": description,
            "date": date or now.strftime("%Y-%m-%d"),
            "created_at": now.isoformat(),
            "from_timer": False
        }
        
        await db.time_entries.insert_one(entry)
        entry.pop("_id", None)
        
        # Process budget cost tracking
        try:
            # Get task to find project_id
            task = await db.tasks.find_one({"task_id": task_id}, {"_id": 0, "project_id": 1})
            if task:
                budget_service = get_budget_service()
                await budget_service.process_time_entry_cost(
                    org_id=org_id,
                    project_id=task["project_id"],
                    task_id=task_id,
                    user_id=user_id,
                    duration_minutes=duration_minutes,
                    time_entry_id=entry_id
                )
        except Exception as e:
            logger.warning(f"Failed to process budget cost for time entry {entry_id}: {e}")
        
        # Update task's actual hours
        await db.tasks.update_one(
            {"task_id": task_id},
            {"$inc": {"actual_hours": duration_minutes / 60}}
        )
        
        entry["created_at"] = now
        return entry
    
    async def update_entry(
        self,
        entry_id: str,
        duration_minutes: int,
        description: str = None,
        date: str = None
    ) -> Tuple[bool, str]:
        """Update a time entry"""
        db = get_database()
        
        entry = await db.time_entries.find_one({"entry_id": entry_id}, {"_id": 0})
        if not entry:
            return False, "Time entry not found"
        
        # Calculate hours difference for task update
        old_minutes = entry["duration_minutes"]
        diff_hours = (duration_minutes - old_minutes) / 60
        
        update_data = {
            "duration_minutes": duration_minutes,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        if description is not None:
            update_data["description"] = description
        if date is not None:
            update_data["date"] = date
        
        await db.time_entries.update_one(
            {"entry_id": entry_id},
            {"$set": update_data}
        )
        
        # Update budget cost if duration changed
        if duration_minutes != old_minutes:
            try:
                # Get task to find project_id
                task = await db.tasks.find_one({"task_id": entry["task_id"]}, {"_id": 0, "project_id": 1})
                if task:
                    budget_service = get_budget_service()
                    # Remove old cost
                    await budget_service.remove_time_entry_cost(entry_id)
                    # Add new cost
                    await budget_service.process_time_entry_cost(
                        org_id=entry["org_id"],
                        project_id=task["project_id"],
                        task_id=entry["task_id"],
                        user_id=entry["user_id"],
                        duration_minutes=duration_minutes,
                        time_entry_id=entry_id
                    )
            except Exception as e:
                logger.warning(f"Failed to update budget cost for time entry {entry_id}: {e}")
        
        # Update task's actual hours
        await db.tasks.update_one(
            {"task_id": entry["task_id"]},
            {"$inc": {"actual_hours": diff_hours}}
        )
        
        return True, "Time entry updated"
    
    async def delete_entry(self, entry_id: str) -> Tuple[bool, str]:
        """Delete a time entry"""
        db = get_database()
        
        entry = await db.time_entries.find_one({"entry_id": entry_id}, {"_id": 0})
        if not entry:
            return False, "Time entry not found"
        
        # Remove budget cost tracking
        try:
            budget_service = get_budget_service()
            await budget_service.remove_time_entry_cost(entry_id)
        except Exception as e:
            logger.warning(f"Failed to remove budget cost for time entry {entry_id}: {e}")
        
        # Update task's actual hours
        await db.tasks.update_one(
            {"task_id": entry["task_id"]},
            {"$inc": {"actual_hours": -(entry["duration_minutes"] / 60)}}
        )
        
        await db.time_entries.delete_one({"entry_id": entry_id})
        
        return True, "Time entry deleted"
    
    async def get_entry(self, entry_id: str) -> Optional[Dict]:
        """Get a single time entry"""
        db = get_database()
        return await db.time_entries.find_one({"entry_id": entry_id}, {"_id": 0})
    
    # =============================================
    # Summaries & Reports
    # =============================================
    
    async def get_summary(
        self,
        user_id: str = None,
        task_ids: List[str] = None,
        start_date: str = None,
        end_date: str = None
    ) -> Dict[str, Any]:
        """Get time summary by user and task"""
        db = get_database()
        
        query = {}
        if task_ids:
            query["task_id"] = {"$in": task_ids}
        elif user_id:
            query["user_id"] = user_id
        
        if start_date:
            query["date"] = {"$gte": start_date}
        if end_date:
            if "date" in query:
                query["date"]["$lte"] = end_date
            else:
                query["date"] = {"$lte": end_date}
        
        entries = await db.time_entries.find(query, {"_id": 0}).to_list(None)
        
        # Aggregate by user and task
        user_totals = {}
        task_totals = {}
        
        for entry in entries:
            uid = entry.get("user_id")
            tid = entry.get("task_id")
            minutes = entry.get("duration_minutes", 0)
            
            if not uid or not tid:
                continue
            
            user_totals[uid] = user_totals.get(uid, 0) + minutes
            task_totals[tid] = task_totals.get(tid, 0) + minutes
        
        # Batch fetch user names
        user_ids = list(user_totals.keys())
        user_map = {}
        if user_ids:
            users = await db.users.find({"user_id": {"$in": user_ids}}, {"_id": 0, "user_id": 1, "name": 1}).to_list(len(user_ids))
            user_map = {u["user_id"]: u.get("name", "Unknown") for u in users}
        
        # Batch fetch task names
        task_ids_list = list(task_totals.keys())
        task_map = {}
        if task_ids_list:
            tasks = await db.tasks.find({"task_id": {"$in": task_ids_list}}, {"_id": 0, "task_id": 1, "title": 1}).to_list(len(task_ids_list))
            task_map = {t["task_id"]: t.get("title", "Unknown") for t in tasks}
        
        user_summary = [
            {
                "user_id": uid,
                "name": user_map.get(uid, "Unknown"),
                "total_minutes": total,
                "total_hours": round(total / 60, 2)
            }
            for uid, total in user_totals.items()
        ]
        
        task_summary = [
            {
                "task_id": tid,
                "title": task_map.get(tid, "Unknown"),
                "total_minutes": total,
                "total_hours": round(total / 60, 2)
            }
            for tid, total in task_totals.items()
        ]
        
        total_minutes = sum(user_totals.values())
        
        return {
            "by_user": sorted(user_summary, key=lambda x: x["total_minutes"], reverse=True),
            "by_task": sorted(task_summary, key=lambda x: x["total_minutes"], reverse=True),
            "total_minutes": total_minutes,
            "total_hours": round(total_minutes / 60, 2)
        }


# Singleton instance
time_service = TimeService()
