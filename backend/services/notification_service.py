"""Enhanced Notification service for in-app, email, and real-time notifications"""
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
import logging
import asyncio

from core.database import get_database
from core.config import settings
from models.notification import (
    NotificationType,
    NotificationChannel,
    DEFAULT_NOTIFICATION_PREFERENCES,
    NotificationPreferencesResponse,
)

logger = logging.getLogger(__name__)


class NotificationService:
    """Service for managing notifications with multi-channel delivery"""
    
    # WebSocket connections for real-time notifications
    _connections: Dict[str, List] = {}
    
    # ==================== WebSocket Management ====================
    
    @classmethod
    def register_connection(cls, user_id: str, websocket):
        """Register a WebSocket connection for a user"""
        if user_id not in cls._connections:
            cls._connections[user_id] = []
        cls._connections[user_id].append(websocket)
        logger.info(f"WebSocket registered for user {user_id}")
    
    @classmethod
    def unregister_connection(cls, user_id: str, websocket):
        """Unregister a WebSocket connection"""
        if user_id in cls._connections:
            cls._connections[user_id] = [
                ws for ws in cls._connections[user_id] if ws != websocket
            ]
            logger.info(f"WebSocket unregistered for user {user_id}")
    
    @classmethod
    async def _send_realtime(cls, user_id: str, notification: Dict):
        """Send real-time notification via WebSocket"""
        if user_id in cls._connections:
            message = {
                "type": "notification",
                "data": {
                    "notification_id": notification["notification_id"],
                    "type": notification["type"],
                    "title": notification["title"],
                    "message": notification["message"],
                    "link": notification.get("link"),
                    "created_at": notification["created_at"]
                }
            }
            
            disconnected = []
            for websocket in cls._connections[user_id]:
                try:
                    await websocket.send_json(message)
                except Exception as e:
                    logger.warning(f"Failed to send WebSocket notification: {e}")
                    disconnected.append(websocket)
            
            # Clean up disconnected sockets
            for ws in disconnected:
                cls._connections[user_id].remove(ws)
    
    # ==================== Preferences Management ====================
    
    @staticmethod
    async def get_user_preferences(user_id: str) -> NotificationPreferencesResponse:
        """Get notification preferences for a user"""
        db = get_database()
        
        prefs = await db.notification_preferences.find_one(
            {"user_id": user_id},
            {"_id": 0}
        )
        
        if not prefs:
            # Return defaults
            return NotificationPreferencesResponse(
                user_id=user_id,
                email_notifications_enabled=True,
                browser_push_enabled=False,
                quiet_hours_enabled=False,
                quiet_hours_start="22:00",
                quiet_hours_end="08:00",
                preferences=DEFAULT_NOTIFICATION_PREFERENCES.copy()
            )
        
        return NotificationPreferencesResponse(**prefs)
    
    @staticmethod
    async def update_user_preferences(user_id: str, updates: Dict) -> NotificationPreferencesResponse:
        """Update notification preferences for a user"""
        db = get_database()
        
        updates["user_id"] = user_id
        updates["updated_at"] = datetime.now(timezone.utc).isoformat()
        
        await db.notification_preferences.update_one(
            {"user_id": user_id},
            {"$set": updates},
            upsert=True
        )
        
        return await NotificationService.get_user_preferences(user_id)
    
    @staticmethod
    async def should_send_notification(
        user_id: str,
        notification_type: str,
        channel: NotificationChannel
    ) -> bool:
        """Check if notification should be sent based on user preferences"""
        prefs = await NotificationService.get_user_preferences(user_id)
        
        # Check global email setting
        if channel == NotificationChannel.EMAIL and not prefs.email_notifications_enabled:
            return False
        
        # Check quiet hours for email
        if channel == NotificationChannel.EMAIL and prefs.quiet_hours_enabled:
            now = datetime.now(timezone.utc)
            current_time = now.strftime("%H:%M")
            start = prefs.quiet_hours_start or "22:00"
            end = prefs.quiet_hours_end or "08:00"
            
            # Simple quiet hours check (doesn't handle overnight spans perfectly)
            if start <= current_time <= end:
                return False
        
        # Check specific notification type preference
        type_prefs = prefs.preferences.get(notification_type, {})
        if not type_prefs.get("enabled", True):
            return False
        
        channels = type_prefs.get("channels", [NotificationChannel.IN_APP.value])
        return channel.value in channels
    
    # ==================== Core Notification Methods ====================
    
    @staticmethod
    async def create(
        user_id: str,
        type: str,
        title: str,
        message: str,
        link: Optional[str] = None,
        metadata: Optional[Dict] = None,
        send_email: bool = True
    ) -> str:
        """
        Create a notification for a user with multi-channel delivery.
        
        Args:
            user_id: Target user ID
            type: Notification type (from NotificationType enum)
            title: Notification title
            message: Notification message
            link: Optional link to related resource
            metadata: Additional metadata
            send_email: Whether to also send email notification
            
        Returns:
            notification_id
        """
        db = get_database()
        
        notification_id = f"notif_{uuid.uuid4().hex[:12]}"
        
        notification = {
            "notification_id": notification_id,
            "user_id": user_id,
            "type": type,
            "title": title,
            "message": message,
            "link": link,
            "metadata": metadata or {},
            "read": False,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        # Always create in-app notification if enabled
        if await NotificationService.should_send_notification(user_id, type, NotificationChannel.IN_APP):
            await db.notifications.insert_one(notification)
            
            # Send real-time notification via WebSocket
            await NotificationService._send_realtime(user_id, notification)
            
            logger.info(f"Notification created for user {user_id}: {title}")
        
        # Send email if enabled
        if send_email and await NotificationService.should_send_notification(user_id, type, NotificationChannel.EMAIL):
            asyncio.create_task(
                NotificationService._send_email_notification(user_id, type, title, message, link, metadata)
            )
        
        return notification_id
    
    @staticmethod
    async def _send_email_notification(
        user_id: str,
        notification_type: str,
        title: str,
        message: str,
        link: Optional[str],
        metadata: Optional[Dict]
    ):
        """Send email notification"""
        from services.email_service import email_service
        
        db = get_database()
        
        # Get user email
        user = await db.users.find_one({"user_id": user_id}, {"email": 1, "name": 1})
        if not user or not user.get("email"):
            logger.warning(f"Cannot send email: User {user_id} not found or no email")
            return
        
        user_email = user["email"]
        user_name = user.get("name", "User")
        
        # Build email based on notification type
        html_content = NotificationService._build_email_html(
            notification_type, title, message, link, metadata, user_name
        )
        
        await email_service.send(
            to=user_email,
            subject=f"{title} - ProFlow",
            html_content=html_content
        )
    
    @staticmethod
    def _build_email_html(
        notification_type: str,
        title: str,
        message: str,
        link: Optional[str],
        metadata: Optional[Dict],
        user_name: str
    ) -> str:
        """Build HTML email content based on notification type"""
        
        # Choose color scheme based on notification type
        type_colors = {
            NotificationType.TASK_ASSIGNED.value: ("#0070f3", "#00c6ff"),
            NotificationType.TASK_OVERDUE.value: ("#ef4444", "#dc2626"),
            NotificationType.TASK_DUE_SOON.value: ("#f59e0b", "#d97706"),
            NotificationType.APPROVAL_APPROVED.value: ("#22c55e", "#16a34a"),
            NotificationType.APPROVAL_REJECTED.value: ("#ef4444", "#dc2626"),
            NotificationType.DOCUMENT_APPROVED.value: ("#22c55e", "#16a34a"),
            NotificationType.DOCUMENT_REJECTED.value: ("#ef4444", "#dc2626"),
            NotificationType.PROJECT_MEMBER_ADDED.value: ("#8b5cf6", "#a855f7"),
            NotificationType.PROJECT_MILESTONE_REACHED.value: ("#10b981", "#059669"),
        }
        
        primary_color, secondary_color = type_colors.get(notification_type, ("#0070f3", "#00c6ff"))
        
        button_html = ""
        if link:
            full_link = link if link.startswith("http") else f"{settings.FRONTEND_URL}{link}"
            button_html = f"""
            <p style="margin: 24px 0; text-align: center;">
                <a href="{full_link}" style="background-color: {primary_color}; color: white; padding: 14px 28px; text-decoration: none; border-radius: 6px; display: inline-block; font-weight: 500;">
                    View Details
                </a>
            </p>
            """
        
        metadata_html = ""
        if metadata:
            items = []
            for key, value in metadata.items():
                if key not in ["user_id", "internal"]:
                    formatted_key = key.replace("_", " ").title()
                    items.append(f"<p style='margin: 4px 0; color: #6a6a6a;'><strong>{formatted_key}:</strong> {value}</p>")
            if items:
                metadata_html = f"""
                <div style="background: #f5f5f5; padding: 16px; border-radius: 8px; margin: 16px 0;">
                    {''.join(items)}
                </div>
                """
        
        return f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background: linear-gradient(135deg, {primary_color} 0%, {secondary_color} 100%); padding: 24px; border-radius: 8px 8px 0 0;">
                <h2 style="color: white; margin: 0;">{title}</h2>
            </div>
            <div style="border: 1px solid #e5e5e5; border-top: none; padding: 24px; border-radius: 0 0 8px 8px;">
                <p style="color: #4a4a4a;">Hi {user_name},</p>
                <p style="color: #4a4a4a;">{message}</p>
                
                {metadata_html}
                {button_html}
                
                <p style="color: #9a9a9a; font-size: 12px; text-align: center; margin-top: 24px;">
                    You're receiving this because of your notification preferences in ProFlow.
                    <br/>
                    <a href="{settings.FRONTEND_URL}/settings?tab=preferences" style="color: #6a6a6a;">Manage preferences</a>
                </p>
            </div>
        </div>
        """
    
    # ==================== Event-Specific Notification Methods ====================
    
    @staticmethod
    async def notify_task_assigned(
        task_id: str,
        task_title: str,
        project_id: str,
        project_name: str,
        assignee_id: str,
        assigner_name: str
    ):
        """Send notification when task is assigned"""
        await NotificationService.create(
            user_id=assignee_id,
            type=NotificationType.TASK_ASSIGNED.value,
            title="New Task Assigned",
            message=f"{assigner_name} assigned you a task: {task_title}",
            link=f"/projects/{project_id}?task={task_id}",
            metadata={
                "task_id": task_id,
                "task_title": task_title,
                "project_id": project_id,
                "project_name": project_name,
                "assigner_name": assigner_name
            }
        )
    
    @staticmethod
    async def notify_task_status_changed(
        task_id: str,
        task_title: str,
        project_id: str,
        old_status: str,
        new_status: str,
        notify_user_ids: List[str],
        changer_name: str
    ):
        """Send notification when task status changes"""
        for user_id in notify_user_ids:
            await NotificationService.create(
                user_id=user_id,
                type=NotificationType.TASK_STATUS_CHANGED.value,
                title="Task Status Updated",
                message=f"{changer_name} changed '{task_title}' from {old_status} to {new_status}",
                link=f"/projects/{project_id}?task={task_id}",
                metadata={
                    "task_id": task_id,
                    "task_title": task_title,
                    "project_id": project_id,
                    "old_status": old_status,
                    "new_status": new_status
                }
            )
    
    @staticmethod
    async def notify_task_due_soon(
        task_id: str,
        task_title: str,
        project_id: str,
        due_date: str,
        assignee_id: str
    ):
        """Send notification when task is due soon (24 hours)"""
        await NotificationService.create(
            user_id=assignee_id,
            type=NotificationType.TASK_DUE_SOON.value,
            title="Task Due Soon",
            message=f"Task '{task_title}' is due on {due_date}",
            link=f"/projects/{project_id}?task={task_id}",
            metadata={
                "task_id": task_id,
                "task_title": task_title,
                "due_date": due_date
            }
        )
    
    @staticmethod
    async def notify_task_overdue(
        task_id: str,
        task_title: str,
        project_id: str,
        due_date: str,
        assignee_id: str
    ):
        """Send notification when task is overdue"""
        await NotificationService.create(
            user_id=assignee_id,
            type=NotificationType.TASK_OVERDUE.value,
            title="Task Overdue",
            message=f"Task '{task_title}' was due on {due_date}",
            link=f"/projects/{project_id}?task={task_id}",
            metadata={
                "task_id": task_id,
                "task_title": task_title,
                "due_date": due_date
            }
        )
    
    @staticmethod
    async def notify_task_comment(
        task_id: str,
        task_title: str,
        project_id: str,
        commenter_name: str,
        comment_preview: str,
        notify_user_ids: List[str]
    ):
        """Send notification for new comment on task"""
        preview = comment_preview[:100] + "..." if len(comment_preview) > 100 else comment_preview
        for user_id in notify_user_ids:
            await NotificationService.create(
                user_id=user_id,
                type=NotificationType.TASK_COMMENT.value,
                title="New Comment",
                message=f"{commenter_name} commented on '{task_title}': {preview}",
                link=f"/projects/{project_id}?task={task_id}",
                metadata={
                    "task_id": task_id,
                    "task_title": task_title,
                    "commenter_name": commenter_name
                }
            )
    
    @staticmethod
    async def notify_mention(
        context_type: str,  # 'task' or 'document'
        context_id: str,
        context_title: str,
        project_id: Optional[str],
        mentioner_name: str,
        mentioned_user_id: str
    ):
        """Send notification when user is @mentioned"""
        link = f"/projects/{project_id}?task={context_id}" if project_id else f"/documents?doc={context_id}"
        await NotificationService.create(
            user_id=mentioned_user_id,
            type=NotificationType.TASK_MENTION.value,
            title="You were mentioned",
            message=f"{mentioner_name} mentioned you in '{context_title}'",
            link=link,
            metadata={
                "context_type": context_type,
                "context_id": context_id,
                "context_title": context_title,
                "mentioner_name": mentioner_name
            }
        )
    
    @staticmethod
    async def notify_project_member_added(
        project_id: str,
        project_name: str,
        added_user_id: str,
        adder_name: str,
        role: str
    ):
        """Send notification when user is added to project"""
        await NotificationService.create(
            user_id=added_user_id,
            type=NotificationType.PROJECT_MEMBER_ADDED.value,
            title="Added to Project",
            message=f"{adder_name} added you to '{project_name}' as {role}",
            link=f"/projects/{project_id}",
            metadata={
                "project_id": project_id,
                "project_name": project_name,
                "role": role
            }
        )
    
    @staticmethod
    async def notify_project_member_removed(
        project_id: str,
        project_name: str,
        removed_user_id: str,
        remover_name: str
    ):
        """Send notification when user is removed from project"""
        await NotificationService.create(
            user_id=removed_user_id,
            type=NotificationType.PROJECT_MEMBER_REMOVED.value,
            title="Removed from Project",
            message=f"{remover_name} removed you from '{project_name}'",
            link="/projects",
            metadata={
                "project_id": project_id,
                "project_name": project_name
            }
        )
    
    @staticmethod
    async def notify_approval_requested(
        approval_type: str,  # 'task' or 'document'
        item_id: str,
        item_title: str,
        requester_name: str,
        approver_ids: List[str],
        link: str
    ):
        """Send notification when approval is requested"""
        notification_type = (
            NotificationType.DOCUMENT_APPROVAL_REQUESTED.value 
            if approval_type == "document" 
            else NotificationType.APPROVAL_REQUESTED.value
        )
        
        for approver_id in approver_ids:
            await NotificationService.create(
                user_id=approver_id,
                type=notification_type,
                title="Approval Required",
                message=f"{requester_name} is requesting your approval for '{item_title}'",
                link=link,
                metadata={
                    "approval_type": approval_type,
                    "item_id": item_id,
                    "item_title": item_title,
                    "requester_name": requester_name
                }
            )
    
    @staticmethod
    async def notify_approval_result(
        approval_type: str,
        item_id: str,
        item_title: str,
        requester_id: str,
        approver_name: str,
        approved: bool,
        link: str,
        comment: Optional[str] = None
    ):
        """Send notification when approval is granted or rejected"""
        if approval_type == "document":
            notification_type = (
                NotificationType.DOCUMENT_APPROVED.value 
                if approved 
                else NotificationType.DOCUMENT_REJECTED.value
            )
        else:
            notification_type = (
                NotificationType.APPROVAL_APPROVED.value 
                if approved 
                else NotificationType.APPROVAL_REJECTED.value
            )
        
        status = "approved" if approved else "rejected"
        
        await NotificationService.create(
            user_id=requester_id,
            type=notification_type,
            title=f"Approval {status.title()}",
            message=f"{approver_name} {status} your request for '{item_title}'",
            link=link,
            metadata={
                "approval_type": approval_type,
                "item_id": item_id,
                "item_title": item_title,
                "approver_name": approver_name,
                "comment": comment
            }
        )
    
    # ==================== Query Methods ====================
    
    @staticmethod
    async def get_user_notifications(
        user_id: str,
        unread_only: bool = False,
        limit: int = 50,
        skip: int = 0,
        notification_type: Optional[str] = None
    ) -> List[Dict]:
        """Get notifications for a user with optional filtering"""
        db = get_database()
        
        query = {"user_id": user_id}
        if unread_only:
            query["read"] = False
        if notification_type:
            query["type"] = notification_type
        
        cursor = db.notifications.find(query, {"_id": 0}).sort("created_at", -1).skip(skip).limit(limit)
        
        return await cursor.to_list(limit)
    
    @staticmethod
    async def get_notifications_paginated(
        user_id: str,
        page: int = 1,
        page_size: int = 20,
        unread_only: bool = False,
        notification_type: Optional[str] = None
    ) -> Dict:
        """Get paginated notifications for a user"""
        db = get_database()
        
        query = {"user_id": user_id}
        if unread_only:
            query["read"] = False
        if notification_type:
            query["type"] = notification_type
        
        total = await db.notifications.count_documents(query)
        skip = (page - 1) * page_size
        
        cursor = db.notifications.find(query, {"_id": 0}).sort("created_at", -1).skip(skip).limit(page_size)
        notifications = await cursor.to_list(page_size)
        
        return {
            "notifications": notifications,
            "total": total,
            "page": page,
            "page_size": page_size,
            "has_more": skip + len(notifications) < total
        }
    
    @staticmethod
    async def mark_as_read(notification_id: str, user_id: str) -> bool:
        """Mark a notification as read"""
        db = get_database()
        
        result = await db.notifications.update_one(
            {"notification_id": notification_id, "user_id": user_id},
            {"$set": {"read": True, "read_at": datetime.now(timezone.utc).isoformat()}}
        )
        
        return result.modified_count > 0
    
    @staticmethod
    async def mark_all_as_read(user_id: str) -> int:
        """Mark all notifications as read for a user"""
        db = get_database()
        
        result = await db.notifications.update_many(
            {"user_id": user_id, "read": False},
            {"$set": {"read": True, "read_at": datetime.now(timezone.utc).isoformat()}}
        )
        
        return result.modified_count
    
    @staticmethod
    async def get_unread_count(user_id: str) -> int:
        """Get count of unread notifications"""
        db = get_database()
        return await db.notifications.count_documents({"user_id": user_id, "read": False})
    
    @staticmethod
    async def delete_notification(notification_id: str, user_id: str) -> bool:
        """Delete a specific notification"""
        db = get_database()
        
        result = await db.notifications.delete_one({
            "notification_id": notification_id,
            "user_id": user_id
        })
        
        return result.deleted_count > 0
    
    @staticmethod
    async def delete_old_notifications(days: int = 30) -> int:
        """Delete notifications older than specified days"""
        db = get_database()
        
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        
        result = await db.notifications.delete_many({
            "created_at": {"$lt": cutoff.isoformat()},
            "read": True
        })
        
        logger.info(f"Deleted {result.deleted_count} old notifications")
        return result.deleted_count


# Singleton instance
notification_service = NotificationService()
