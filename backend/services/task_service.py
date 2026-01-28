"""Task Service - Business logic for task management"""
from datetime import datetime, timezone
from typing import List, Dict, Optional, Tuple, Any
import uuid
import logging
import os
from pathlib import Path

from core.database import get_database
from repositories.task_repository import task_repository
from repositories.project_repository import project_repository
from services.audit_service import audit_service
from services.notification_service import notification_service

logger = logging.getLogger(__name__)

UPLOAD_DIR = Path(__file__).parent.parent / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)


class TaskService:
    """Service for task business logic"""
    
    def __init__(self):
        self.repo = task_repository
    
    # =============================================
    # Task CRUD
    # =============================================
    
    async def get_tasks(
        self,
        project_id: str = None,
        project_ids: List[str] = None,
        status: str = None,
        assignee_id: str = None
    ) -> List[Dict]:
        """Get tasks with optional filters"""
        if project_id:
            tasks = await self.repo.find_by_project(project_id, status=status, assignee_id=assignee_id)
        elif project_ids:
            query = {"project_id": {"$in": project_ids}}
            if status:
                query["status"] = status
            if assignee_id:
                query["assignee_ids"] = assignee_id
            tasks = await self.repo.find_all(query)
        else:
            tasks = []
        
        for task in tasks:
            task["created_at"] = self._parse_datetime(task.get("created_at"))
            task["updated_at"] = self._parse_datetime(task.get("updated_at", task.get("created_at")))
        
        return tasks
    
    async def get_task(self, task_id: str) -> Optional[Dict]:
        """Get a single task by ID"""
        task = await self.repo.find_by_id(task_id)
        if task:
            task["created_at"] = self._parse_datetime(task.get("created_at"))
            task["updated_at"] = self._parse_datetime(task.get("updated_at", task.get("created_at")))
        return task
    
    async def create_task(
        self,
        user_id: str,
        user_name: str,
        project_id: str,
        org_id: str,
        title: str,
        description: str = None,
        status: str = "todo",
        priority: str = "medium",
        due_date: str = None,
        start_date: str = None,
        assignee_ids: List[str] = None,
        dependencies: List[str] = None,
        subtasks: List[Dict] = None,
        estimated_hours: float = None,
        recurring_rule: str = None,
        baseline_start: str = None,
        baseline_end: str = None
    ) -> Dict:
        """Create a new task"""
        task_data = {
            "project_id": project_id,
            "org_id": org_id,
            "title": title,
            "description": description,
            "status": status,
            "priority": priority,
            "due_date": due_date,
            "start_date": start_date,
            "assignee_ids": assignee_ids or [],
            "dependencies": dependencies or [],
            "subtasks": subtasks or [],
            "estimated_hours": estimated_hours,
            "actual_hours": 0,
            "recurring_rule": recurring_rule,
            "baseline_start": baseline_start,
            "baseline_end": baseline_end,
            "created_by": user_id,
        }
        
        task = await self.repo.create(task_data)
        
        # Get project name for notification context
        project = await project_repository.find_by_id(project_id)
        project_name = project.get("name", "Unknown Project") if project else "Unknown Project"
        
        # Notify assignees
        for assignee_id in (assignee_ids or []):
            if assignee_id != user_id:
                await notification_service.notify_task_assigned(
                    task_id=task['task_id'],
                    task_title=title,
                    project_id=project_id,
                    project_name=project_name,
                    assignee_id=assignee_id,
                    assigner_name=user_name
                )
        
        await audit_service.log(user_id, org_id, "create", "task", task["task_id"])
        
        task["created_at"] = self._parse_datetime(task["created_at"])
        task["updated_at"] = self._parse_datetime(task["updated_at"])
        
        return task
    
    async def update_task(
        self,
        task_id: str,
        user_id: str,
        updates: Dict
    ) -> Tuple[bool, str, Optional[Dict]]:
        """Update a task"""
        task = await self.repo.find_by_id(task_id)
        if not task:
            return False, "Task not found", None
        
        # Check if task is locked
        if task.get("approval_locked", False):
            return False, "Task is locked pending approval", None
        
        old_assignees = set(task.get("assignee_ids", []))
        old_status = task.get("status")
        
        # Filter valid updates
        update_data = {k: v for k, v in updates.items() if v is not None}
        
        # Check for new assignees
        new_assignees = set(update_data.get("assignee_ids", old_assignees))
        added_assignees = new_assignees - old_assignees
        
        # Get project name for notifications
        project = await project_repository.find_by_id(task.get("project_id"))
        project_name = project.get("name", "Unknown Project") if project else "Unknown Project"
        
        # Notify new assignees
        for assignee_id in added_assignees:
            if assignee_id != user_id:
                db = get_database()
                current_user = await db.users.find_one({"user_id": user_id}, {"name": 1})
                user_name = current_user.get("name", "Someone") if current_user else "Someone"
                
                await notification_service.notify_task_assigned(
                    task_id=task_id,
                    task_title=task['title'],
                    project_id=task['project_id'],
                    project_name=project_name,
                    assignee_id=assignee_id,
                    assigner_name=user_name
                )
        
        # Check for status change
        new_status = update_data.get("status")
        if new_status and new_status != old_status:
            # Notify all assignees about status change (except the one who changed it)
            notify_user_ids = [aid for aid in task.get("assignee_ids", []) if aid != user_id]
            if notify_user_ids:
                db = get_database()
                current_user = await db.users.find_one({"user_id": user_id}, {"name": 1})
                user_name = current_user.get("name", "Someone") if current_user else "Someone"
                
                await notification_service.notify_task_status_changed(
                    task_id=task_id,
                    task_title=task['title'],
                    project_id=task['project_id'],
                    old_status=old_status,
                    new_status=new_status,
                    notify_user_ids=notify_user_ids,
                    changer_name=user_name
                )
        
        if update_data:
            await self.repo.update(task_id, update_data)
        
        await audit_service.log(user_id, task["org_id"], "update", "task", task_id, update_data)
        
        # Return updated task
        updated_task = await self.get_task(task_id)
        return True, "Task updated", updated_task
    
    async def delete_task(self, task_id: str, user_id: str) -> Tuple[bool, str]:
        """Delete a task and related data"""
        db = get_database()
        
        task = await self.repo.find_by_id(task_id)
        if not task:
            return False, "Task not found"
        
        # Delete related data
        await db.comments.delete_many({"task_id": task_id})
        await db.time_entries.delete_many({"task_id": task_id})
        await db.attachments.delete_many({"task_id": task_id})
        
        await self.repo.delete(task_id)
        
        await audit_service.log(user_id, task["org_id"], "delete", "task", task_id)
        
        return True, "Task deleted successfully"
    
    # =============================================
    # Checklist / Subtasks
    # =============================================
    
    async def add_checklist_item(
        self,
        task_id: str,
        title: str,
        completed: bool = False
    ) -> Dict:
        """Add a checklist item to a task"""
        db = get_database()
        
        item_id = f"item_{uuid.uuid4().hex[:8]}"
        checklist_item = {
            "item_id": item_id,
            "title": title,
            "completed": completed,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        await db.tasks.update_one(
            {"task_id": task_id},
            {
                "$push": {"subtasks": checklist_item},
                "$set": {"updated_at": datetime.now(timezone.utc).isoformat()}
            }
        )
        
        return checklist_item
    
    async def update_checklist_item(
        self,
        task_id: str,
        item_id: str,
        title: str = None,
        completed: bool = None
    ) -> bool:
        """Update a checklist item"""
        db = get_database()
        
        update_fields = {"updated_at": datetime.now(timezone.utc).isoformat()}
        if title is not None:
            update_fields["subtasks.$.title"] = title
        if completed is not None:
            update_fields["subtasks.$.completed"] = completed
        
        result = await db.tasks.update_one(
            {"task_id": task_id, "subtasks.item_id": item_id},
            {"$set": update_fields}
        )
        
        return result.modified_count > 0
    
    async def delete_checklist_item(self, task_id: str, item_id: str) -> bool:
        """Delete a checklist item"""
        db = get_database()
        
        result = await db.tasks.update_one(
            {"task_id": task_id},
            {
                "$pull": {"subtasks": {"item_id": item_id}},
                "$set": {"updated_at": datetime.now(timezone.utc).isoformat()}
            }
        )
        
        return result.modified_count > 0
    
    # =============================================
    # Dependencies
    # =============================================
    
    async def update_dependencies(self, task_id: str, dependencies: List[str]) -> bool:
        """Update task dependencies"""
        return await self.repo.update(task_id, {"dependencies": dependencies})
    
    # =============================================
    # Attachments
    # =============================================
    
    async def upload_attachment(
        self,
        task_id: str,
        org_id: str,
        user_id: str,
        filename: str,
        content: bytes,
        content_type: str
    ) -> Dict:
        """Upload an attachment to a task"""
        db = get_database()
        
        attachment_id = f"att_{uuid.uuid4().hex[:12]}"
        stored_filename = f"{attachment_id}_{filename}"
        filepath = UPLOAD_DIR / stored_filename
        
        with open(filepath, 'wb') as f:
            f.write(content)
        
        attachment = {
            "attachment_id": attachment_id,
            "task_id": task_id,
            "org_id": org_id,
            "filename": stored_filename,
            "original_filename": filename,
            "content_type": content_type,
            "size": len(content),
            "uploaded_by": user_id,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        await db.attachments.insert_one(attachment)
        attachment.pop("_id", None)
        
        return attachment
    
    async def get_attachments(self, task_id: str) -> List[Dict]:
        """Get all attachments for a task"""
        db = get_database()
        return await db.attachments.find({"task_id": task_id}, {"_id": 0}).to_list(100)
    
    async def delete_attachment(self, attachment_id: str) -> bool:
        """Delete an attachment"""
        db = get_database()
        
        attachment = await db.attachments.find_one({"attachment_id": attachment_id}, {"_id": 0})
        if attachment:
            filepath = UPLOAD_DIR / attachment["filename"]
            if filepath.exists():
                os.remove(filepath)
        
        result = await db.attachments.delete_one({"attachment_id": attachment_id})
        return result.deleted_count > 0
    
    # =============================================
    # Activity
    # =============================================
    
    async def get_activity(self, task_id: str, org_id: str) -> List[Dict]:
        """Get task activity log"""
        db = get_database()
        
        logs = await audit_service.get_logs(
            org_id=org_id,
            resource_type="task",
            resource_id=task_id,
            limit=50
        )
        
        user_ids = list(set([log["user_id"] for log in logs if log.get("user_id")]))
        user_map = {}
        if user_ids:
            users = await db.users.find(
                {"user_id": {"$in": user_ids}},
                {"_id": 0, "user_id": 1, "name": 1}
            ).to_list(100)
            user_map = {u["user_id"]: u.get("name", "Unknown") for u in users}
        
        for log in logs:
            log["user_name"] = user_map.get(log.get("user_id"), "Unknown")
        
        return logs
    
    # =============================================
    # Bulk Operations
    # =============================================
    
    async def bulk_update(
        self,
        task_ids: List[str],
        updates: Dict,
        user_id: str
    ) -> Tuple[bool, int]:
        """Bulk update multiple tasks"""
        db = get_database()
        
        allowed_fields = {"status", "priority", "due_date"}
        filtered_updates = {k: v for k, v in updates.items() if k in allowed_fields}
        
        if not filtered_updates:
            return False, 0
        
        filtered_updates["updated_at"] = datetime.now(timezone.utc).isoformat()
        
        result = await db.tasks.update_many(
            {"task_id": {"$in": task_ids}},
            {"$set": filtered_updates}
        )
        
        # Audit log for each task
        tasks = await self.repo.find_all({"task_id": {"$in": task_ids}})
        for task in tasks:
            await audit_service.log(
                user_id,
                task["org_id"],
                "bulk_update",
                "task",
                task["task_id"],
                {"updates": filtered_updates, "batch_size": len(task_ids)}
            )
        
        return True, result.modified_count
    
    async def bulk_assign(
        self,
        task_ids: List[str],
        assignee_id: str,
        user_id: str
    ) -> Tuple[bool, int]:
        """Bulk assign a user to multiple tasks"""
        db = get_database()
        
        tasks = await self.repo.find_all({"task_id": {"$in": task_ids}})
        
        now = datetime.now(timezone.utc).isoformat()
        modified_count = 0
        
        for task in tasks:
            current_assignees = task.get("assignee_ids", []) or []
            if assignee_id not in current_assignees:
                await db.tasks.update_one(
                    {"task_id": task["task_id"]},
                    {
                        "$addToSet": {"assignee_ids": assignee_id},
                        "$set": {"updated_at": now}
                    }
                )
                modified_count += 1
                
                await notification_service.create(
                    user_id=assignee_id,
                    type="task_assigned",
                    title="New Task Assigned",
                    message=f"You have been assigned to: {task.get('title', 'Untitled')}",
                    link=f"/projects/{task.get('project_id')}?task={task['task_id']}"
                )
        
        return True, modified_count
    
    async def bulk_delete(
        self,
        task_ids: List[str],
        user_id: str
    ) -> Tuple[bool, int]:
        """Bulk delete multiple tasks"""
        db = get_database()
        
        tasks = await self.repo.find_all({"task_id": {"$in": task_ids}})
        
        # Delete related data
        await db.comments.delete_many({"task_id": {"$in": task_ids}})
        await db.time_entries.delete_many({"task_id": {"$in": task_ids}})
        await db.attachments.delete_many({"task_id": {"$in": task_ids}})
        
        result = await db.tasks.delete_many({"task_id": {"$in": task_ids}})
        
        # Clean up dependencies
        await db.tasks.update_many(
            {"blocked_by": {"$in": task_ids}},
            {"$pullAll": {"blocked_by": task_ids}}
        )
        await db.tasks.update_many(
            {"blocks": {"$in": task_ids}},
            {"$pullAll": {"blocks": task_ids}}
        )
        
        # Audit log
        for task in tasks:
            await audit_service.log(
                user_id,
                task["org_id"],
                "bulk_delete",
                "task",
                task["task_id"],
                {"title": task.get("title"), "batch_size": len(task_ids)}
            )
        
        return True, result.deleted_count
    
    # =============================================
    # Utilities
    # =============================================
    
    def _parse_datetime(self, dt_value) -> datetime:
        """Parse datetime from string or return as-is"""
        if isinstance(dt_value, str):
            return datetime.fromisoformat(dt_value.replace("Z", "+00:00"))
        return dt_value


# Singleton instance
task_service = TaskService()
