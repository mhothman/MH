"""Notification router with full CRUD and preferences support"""
from fastapi import APIRouter, HTTPException, Request, WebSocket, WebSocketDisconnect, Query
from datetime import datetime, timezone
from typing import List, Optional
import logging

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.database import get_database
from core.security import require_auth, decode_jwt_token
from core.config import settings
from services.notification_service import notification_service
from models.notification import (
    NotificationType,
    NotificationPreferencesUpdate,
    NotificationPreferencesResponse,
    NotificationListResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter()


# ==================== Notification Endpoints ====================

@router.get("/")
async def get_notifications(
    request: Request, 
    unread_only: bool = False, 
    limit: int = Query(50, le=100),
    notification_type: Optional[str] = None
):
    """Get notifications for current user"""
    user = await require_auth(request)
    
    notifications = await notification_service.get_user_notifications(
        user["user_id"],
        unread_only=unread_only,
        limit=limit,
        notification_type=notification_type
    )
    
    return notifications


@router.get("/paginated")
async def get_notifications_paginated(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    unread_only: bool = False,
    notification_type: Optional[str] = None
):
    """Get paginated notifications for current user"""
    user = await require_auth(request)
    
    result = await notification_service.get_notifications_paginated(
        user["user_id"],
        page=page,
        page_size=page_size,
        unread_only=unread_only,
        notification_type=notification_type
    )
    
    return result


@router.get("/types")
async def get_notification_types(request: Request):
    """Get all available notification types with descriptions"""
    await require_auth(request)
    
    type_descriptions = {
        NotificationType.TASK_ASSIGNED.value: {
            "label": "Task Assigned",
            "description": "When a task is assigned to you",
            "category": "Tasks"
        },
        NotificationType.TASK_STATUS_CHANGED.value: {
            "label": "Task Status Changed",
            "description": "When a task you're involved with changes status",
            "category": "Tasks"
        },
        NotificationType.TASK_DUE_SOON.value: {
            "label": "Task Due Soon",
            "description": "When a task is due within 24 hours",
            "category": "Tasks"
        },
        NotificationType.TASK_OVERDUE.value: {
            "label": "Task Overdue",
            "description": "When a task passes its due date",
            "category": "Tasks"
        },
        NotificationType.TASK_COMMENT.value: {
            "label": "Task Comment",
            "description": "When someone comments on a task you're involved with",
            "category": "Tasks"
        },
        NotificationType.TASK_MENTION.value: {
            "label": "Mentions",
            "description": "When someone @mentions you",
            "category": "Tasks"
        },
        NotificationType.DOCUMENT_APPROVAL_REQUESTED.value: {
            "label": "Document Approval Requested",
            "description": "When document approval is requested from you",
            "category": "Documents"
        },
        NotificationType.DOCUMENT_APPROVED.value: {
            "label": "Document Approved",
            "description": "When your document is approved",
            "category": "Documents"
        },
        NotificationType.DOCUMENT_REJECTED.value: {
            "label": "Document Rejected",
            "description": "When your document is rejected",
            "category": "Documents"
        },
        NotificationType.DOCUMENT_STATUS_CHANGED.value: {
            "label": "Document Status Changed",
            "description": "When a document status changes",
            "category": "Documents"
        },
        NotificationType.PROJECT_MEMBER_ADDED.value: {
            "label": "Added to Project",
            "description": "When you're added to a project",
            "category": "Projects"
        },
        NotificationType.PROJECT_MEMBER_REMOVED.value: {
            "label": "Removed from Project",
            "description": "When you're removed from a project",
            "category": "Projects"
        },
        NotificationType.PROJECT_STATUS_CHANGED.value: {
            "label": "Project Status Changed",
            "description": "When a project status changes",
            "category": "Projects"
        },
        NotificationType.PROJECT_MILESTONE_REACHED.value: {
            "label": "Project Milestone",
            "description": "When a project milestone is reached",
            "category": "Projects"
        },
        NotificationType.APPROVAL_REQUESTED.value: {
            "label": "Approval Requested",
            "description": "When task approval is requested from you",
            "category": "Approvals"
        },
        NotificationType.APPROVAL_APPROVED.value: {
            "label": "Approval Granted",
            "description": "When your approval request is granted",
            "category": "Approvals"
        },
        NotificationType.APPROVAL_REJECTED.value: {
            "label": "Approval Rejected",
            "description": "When your approval request is rejected",
            "category": "Approvals"
        },
        NotificationType.SYSTEM_ANNOUNCEMENT.value: {
            "label": "System Announcements",
            "description": "Important system updates and announcements",
            "category": "System"
        },
        NotificationType.WEEKLY_DIGEST.value: {
            "label": "Weekly Digest",
            "description": "Weekly summary of your activity",
            "category": "System"
        },
    }
    
    # Group by category
    categories = {}
    for type_id, info in type_descriptions.items():
        category = info["category"]
        if category not in categories:
            categories[category] = []
        categories[category].append({
            "type": type_id,
            **info
        })
    
    return {
        "types": type_descriptions,
        "categories": categories
    }


@router.get("/unread-count")
async def get_unread_count(request: Request):
    """Get unread notification count"""
    user = await require_auth(request)
    count = await notification_service.get_unread_count(user["user_id"])
    return {"count": count}


@router.put("/{notification_id}/read")
async def mark_notification_read(notification_id: str, request: Request):
    """Mark a notification as read"""
    user = await require_auth(request)
    
    success = await notification_service.mark_as_read(notification_id, user["user_id"])
    if not success:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    return {"message": "Notification marked as read"}


@router.put("/read-all")
async def mark_all_notifications_read(request: Request):
    """Mark all notifications as read"""
    user = await require_auth(request)
    
    count = await notification_service.mark_all_as_read(user["user_id"])
    
    return {"message": f"Marked {count} notifications as read", "count": count}


@router.delete("/{notification_id}")
async def delete_notification(notification_id: str, request: Request):
    """Delete a notification"""
    user = await require_auth(request)
    
    success = await notification_service.delete_notification(notification_id, user["user_id"])
    if not success:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    return {"message": "Notification deleted"}


# ==================== Notification Preferences Endpoints ====================

@router.get("/preferences")
async def get_notification_preferences(request: Request):
    """Get notification preferences for current user"""
    user = await require_auth(request)
    
    prefs = await notification_service.get_user_preferences(user["user_id"])
    return prefs


@router.put("/preferences")
async def update_notification_preferences(
    request: Request,
    updates: NotificationPreferencesUpdate
):
    """Update notification preferences for current user"""
    user = await require_auth(request)
    
    updated_prefs = await notification_service.update_user_preferences(
        user["user_id"],
        updates.model_dump(exclude_unset=True)
    )
    
    return updated_prefs


@router.put("/preferences/{notification_type}")
async def update_single_preference(
    notification_type: str,
    request: Request,
    enabled: bool = True,
    channels: List[str] = ["in_app"]
):
    """Update preference for a single notification type"""
    user = await require_auth(request)
    
    # Validate notification type
    valid_types = [t.value for t in NotificationType]
    if notification_type not in valid_types:
        raise HTTPException(status_code=400, detail=f"Invalid notification type: {notification_type}")
    
    # Get current preferences
    prefs = await notification_service.get_user_preferences(user["user_id"])
    
    # Update the specific type
    prefs_dict = prefs.model_dump()
    prefs_dict["preferences"][notification_type] = {
        "enabled": enabled,
        "channels": channels
    }
    
    # Save
    updated_prefs = await notification_service.update_user_preferences(
        user["user_id"],
        {"preferences": prefs_dict["preferences"]}
    )
    
    return updated_prefs


# ==================== WebSocket Endpoint ====================

@router.websocket("/ws/{token}")
async def websocket_endpoint(websocket: WebSocket, token: str):
    """WebSocket endpoint for real-time notifications"""
    await websocket.accept()
    
    # Verify token
    payload = decode_jwt_token(token)
    if not payload:
        await websocket.close(code=4001)
        return
    
    user_id = payload.get("user_id")
    if not user_id:
        await websocket.close(code=4001)
        return
    
    # Register connection
    notification_service.register_connection(user_id, websocket)
    
    try:
        # Send initial unread count
        count = await notification_service.get_unread_count(user_id)
        await websocket.send_json({
            "type": "init",
            "data": {"unread_count": count}
        })
        
        while True:
            # Keep connection alive
            data = await websocket.receive_text()
            
            if data == "ping":
                await websocket.send_text("pong")
            elif data == "get_count":
                count = await notification_service.get_unread_count(user_id)
                await websocket.send_json({
                    "type": "count",
                    "data": {"unread_count": count}
                })
    except WebSocketDisconnect:
        notification_service.unregister_connection(user_id, websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        notification_service.unregister_connection(user_id, websocket)
