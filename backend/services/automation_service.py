"""Automation Engine Service - Business logic for automation execution"""
import uuid
import logging
import asyncio
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple, Any
import httpx

from core.database import get_database
from services.notification_service import notification_service
from services.email_service import email_service
from services.audit_service import audit_service

logger = logging.getLogger(__name__)


# =============================================
# Constants
# =============================================

TRIGGER_TYPES = [
    {"type": "task_created", "name": "Task Created", "description": "When a new task is created"},
    {"type": "task_updated", "name": "Task Updated", "description": "When a task is modified"},
    {"type": "status_changed", "name": "Status Changed", "description": "When task status changes"},
    {"type": "priority_changed", "name": "Priority Changed", "description": "When task priority changes"},
    {"type": "deadline_reached", "name": "Deadline Reached", "description": "When task due date is reached"},
    {"type": "task_assigned", "name": "Task Assigned", "description": "When a task is assigned to someone"},
    {"type": "comment_added", "name": "Comment Added", "description": "When a comment is added to a task"}
]

ACTION_TYPES = [
    {"type": "notify_users", "name": "Notify Users", "description": "Send notification to users"},
    {"type": "assign_task", "name": "Assign Task", "description": "Assign the task to a user"},
    {"type": "update_task", "name": "Update Task", "description": "Update task fields"},
    {"type": "call_webhook", "name": "Call Webhook", "description": "Send HTTP request to a URL"},
    {"type": "send_email", "name": "Send Email", "description": "Send email to a user"}
]

VALID_TRIGGER_TYPES = {t["type"] for t in TRIGGER_TYPES}
VALID_ACTION_TYPES = {a["type"] for a in ACTION_TYPES}


class AutomationService:
    """Service for automation CRUD and business logic"""
    
    # =============================================
    # CRUD Operations
    # =============================================
    
    async def get_automations(self, org_id: str) -> List[Dict]:
        """Get all automations for an organization"""
        db = get_database()
        return await db.automations.find({"org_id": org_id}, {"_id": 0}).to_list(100)
    
    async def get_automation(self, automation_id: str) -> Optional[Dict]:
        """Get a specific automation"""
        db = get_database()
        return await db.automations.find_one({"automation_id": automation_id}, {"_id": 0})
    
    async def create_automation(
        self,
        org_id: str,
        user_id: str,
        name: str,
        trigger: Dict,
        actions: List[Dict],
        description: str = None,
        enabled: bool = True
    ) -> Tuple[bool, str, Optional[Dict]]:
        """Create a new automation"""
        db = get_database()
        
        # Validate trigger type
        if trigger.get("type") not in VALID_TRIGGER_TYPES:
            return False, f"Invalid trigger type: {trigger.get('type')}", None
        
        # Validate action types
        for action in actions:
            if action.get("type") not in VALID_ACTION_TYPES:
                return False, f"Invalid action type: {action.get('type')}", None
        
        automation_id = f"auto_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc).isoformat()
        
        automation = {
            "automation_id": automation_id,
            "org_id": org_id,
            "name": name,
            "description": description,
            "trigger": trigger,
            "actions": actions,
            "enabled": enabled,
            "created_by": user_id,
            "run_count": 0,
            "last_run": None,
            "created_at": now,
            "updated_at": now
        }
        
        await db.automations.insert_one(automation)
        await audit_service.log(user_id, org_id, "create", "automation", automation_id)
        
        automation.pop("_id", None)
        return True, "Automation created", automation
    
    async def update_automation(
        self,
        automation_id: str,
        user_id: str,
        org_id: str,
        name: str = None,
        description: str = None,
        trigger: Dict = None,
        actions: List[Dict] = None,
        enabled: bool = None
    ) -> Tuple[bool, str]:
        """Update an automation"""
        db = get_database()
        
        update_data = {"updated_at": datetime.now(timezone.utc).isoformat()}
        
        if name is not None:
            update_data["name"] = name
        if description is not None:
            update_data["description"] = description
        if trigger is not None:
            if trigger.get("type") not in VALID_TRIGGER_TYPES:
                return False, f"Invalid trigger type: {trigger.get('type')}"
            update_data["trigger"] = trigger
        if actions is not None:
            for action in actions:
                if action.get("type") not in VALID_ACTION_TYPES:
                    return False, f"Invalid action type: {action.get('type')}"
            update_data["actions"] = actions
        if enabled is not None:
            update_data["enabled"] = enabled
        
        await db.automations.update_one(
            {"automation_id": automation_id},
            {"$set": update_data}
        )
        
        await audit_service.log(user_id, org_id, "update", "automation", automation_id)
        return True, "Automation updated"
    
    async def delete_automation(self, automation_id: str, user_id: str, org_id: str) -> Tuple[bool, str]:
        """Delete an automation"""
        db = get_database()
        
        result = await db.automations.delete_one({"automation_id": automation_id})
        if result.deleted_count == 0:
            return False, "Automation not found"
        
        await audit_service.log(user_id, org_id, "delete", "automation", automation_id)
        return True, "Automation deleted"
    
    async def get_history(self, automation_id: str, limit: int = 50) -> List[Dict]:
        """Get execution history for an automation"""
        db = get_database()
        return await db.automation_runs.find(
            {"automation_id": automation_id},
            {"_id": 0}
        ).sort("executed_at", -1).limit(limit).to_list(limit)
    
    def get_trigger_types(self) -> List[Dict]:
        """Get available trigger types"""
        return TRIGGER_TYPES
    
    def get_action_types(self) -> List[Dict]:
        """Get available action types"""
        return ACTION_TYPES


class AutomationEngine:
    """Engine for executing automations based on triggers"""
    
    @staticmethod
    async def trigger_event(event_type: str, event_data: Dict, org_id: str):
        """
        Trigger automations based on an event.
        
        Args:
            event_type: Type of event (task_created, task_updated, etc.)
            event_data: Data associated with the event
            org_id: Organization ID
        """
        db = get_database()
        
        # Find matching automations
        automations = await db.automations.find({
            "org_id": org_id,
            "enabled": True,
            "trigger.type": event_type
        }, {"_id": 0}).to_list(100)
        
        for automation in automations:
            # Check if conditions match
            if await AutomationEngine._check_conditions(automation.get("trigger", {}).get("conditions", []), event_data):
                await AutomationEngine._execute_automation(automation, event_data)
    
    @staticmethod
    async def _check_conditions(conditions: List[Dict], event_data: Dict) -> bool:
        """Check if all conditions are met"""
        if not conditions:
            return True
        
        for condition in conditions:
            field = condition.get("field", "")
            operator = condition.get("operator", "equals")
            value = condition.get("value")
            
            actual_value = event_data.get(field)
            
            if operator == "equals" and actual_value != value:
                return False
            elif operator == "not_equals" and actual_value == value:
                return False
            elif operator == "contains" and value not in str(actual_value):
                return False
            elif operator == "in" and actual_value not in value:
                return False
        
        return True
    
    @staticmethod
    async def _execute_automation(automation: Dict, event_data: Dict):
        """Execute all actions in an automation"""
        db = get_database()
        run_id = f"run_{uuid.uuid4().hex[:12]}"
        started_at = datetime.now(timezone.utc)
        
        results = []
        success = True
        
        for action in automation.get("actions", []):
            try:
                result = await AutomationEngine._execute_action(action, event_data, automation["org_id"])
                results.append(result)
                if not result.get("success"):
                    success = False
            except Exception as e:
                logger.error(f"Action execution failed: {e}")
                success = False
                results.append({"error": str(e)})
        
        # Record run
        run_record = {
            "run_id": run_id,
            "automation_id": automation["automation_id"],
            "org_id": automation["org_id"],
            "trigger_data": event_data,
            "results": results,
            "success": success,
            "executed_at": started_at.isoformat(),
            "duration_ms": int((datetime.now(timezone.utc) - started_at).total_seconds() * 1000)
        }
        await db.automation_runs.insert_one(run_record)
        
        # Update automation stats
        await db.automations.update_one(
            {"automation_id": automation["automation_id"]},
            {
                "$inc": {"run_count": 1},
                "$set": {"last_run": started_at.isoformat()}
            }
        )
        
        logger.info(f"Automation {automation['automation_id']} executed: success={success}")
    
    @staticmethod
    async def _execute_action(action: Dict, event_data: Dict, org_id: str) -> Dict:
        """Execute a single action"""
        action_type = action["type"]
        config = action.get("config", {})
        
        try:
            if action_type == "notify_users":
                return await AutomationEngine._action_notify_users(config, event_data, org_id)
            elif action_type == "assign_task":
                return await AutomationEngine._action_assign_task(config, event_data)
            elif action_type == "update_task":
                return await AutomationEngine._action_update_task(config, event_data)
            elif action_type == "call_webhook":
                return await AutomationEngine._action_call_webhook(config, event_data)
            elif action_type == "send_email":
                return await AutomationEngine._action_send_email(config, event_data, org_id)
            else:
                return {"success": False, "error": f"Unknown action type: {action_type}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def _action_notify_users(config: Dict, event_data: Dict, org_id: str) -> Dict:
        """Send notifications to users"""
        user_ids = config.get("user_ids", [])
        title = config.get("title", "Automation Notification")
        message = config.get("message", "")
        
        # Replace placeholders in message
        for key, value in event_data.items():
            message = message.replace(f"{{{key}}}", str(value))
        
        for user_id in user_ids:
            await notification_service.create(
                user_id=user_id,
                type="automation",
                title=title,
                message=message,
                link=config.get("link")
            )
        
        return {"success": True, "notified": len(user_ids)}
    
    @staticmethod
    async def _action_assign_task(config: Dict, event_data: Dict) -> Dict:
        """Assign task to users"""
        db = get_database()
        task_id = event_data.get("task_id")
        assignee_ids = config.get("assignee_ids", [])
        
        if not task_id:
            return {"success": False, "error": "No task_id in event data"}
        
        await db.tasks.update_one(
            {"task_id": task_id},
            {"$set": {"assignee_ids": assignee_ids}}
        )
        
        return {"success": True, "assigned_to": assignee_ids}
    
    @staticmethod
    async def _action_update_task(config: Dict, event_data: Dict) -> Dict:
        """Update task fields"""
        db = get_database()
        task_id = event_data.get("task_id")
        
        if not task_id:
            return {"success": False, "error": "No task_id in event data"}
        
        update_fields = config.get("fields", {})
        update_fields["updated_at"] = datetime.now(timezone.utc).isoformat()
        
        await db.tasks.update_one(
            {"task_id": task_id},
            {"$set": update_fields}
        )
        
        return {"success": True, "updated_fields": list(update_fields.keys())}
    
    @staticmethod
    async def _action_call_webhook(config: Dict, event_data: Dict) -> Dict:
        """Call an external webhook"""
        url = config.get("url")
        method = config.get("method", "POST").upper()
        headers = config.get("headers", {})
        
        if not url:
            return {"success": False, "error": "No webhook URL configured"}
        
        try:
            async with httpx.AsyncClient() as client:
                if method == "POST":
                    response = await client.post(url, json=event_data, headers=headers, timeout=30)
                elif method == "GET":
                    response = await client.get(url, params=event_data, headers=headers, timeout=30)
                else:
                    return {"success": False, "error": f"Unsupported method: {method}"}
                
                return {
                    "success": response.status_code < 400,
                    "status_code": response.status_code,
                    "response": response.text[:500]
                }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    @staticmethod
    async def _action_send_email(config: Dict, event_data: Dict, org_id: str) -> Dict:
        """Send email to users"""
        db = get_database()
        user_ids = config.get("user_ids", [])
        subject = config.get("subject", "Automation Email")
        body = config.get("body", "")
        
        # Replace placeholders
        for key, value in event_data.items():
            subject = subject.replace(f"{{{key}}}", str(value))
            body = body.replace(f"{{{key}}}", str(value))
        
        sent_count = 0
        for user_id in user_ids:
            user = await db.users.find_one({"user_id": user_id}, {"_id": 0, "email": 1, "name": 1})
            if user and user.get("email"):
                try:
                    await email_service.send_email(
                        to_email=user["email"],
                        to_name=user.get("name", "User"),
                        subject=subject,
                        html_content=f"<div>{body}</div>"
                    )
                    sent_count += 1
                except Exception as e:
                    logger.error(f"Failed to send email to {user['email']}: {e}")
        
        return {"success": True, "emails_sent": sent_count}


# Singleton instances
automation_service = AutomationService()
automation_engine = AutomationEngine()
