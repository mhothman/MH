"""Notification models and types"""
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict
from datetime import datetime
from enum import Enum


class NotificationType(str, Enum):
    """Types of notifications"""
    # Task events
    TASK_ASSIGNED = "task_assigned"
    TASK_STATUS_CHANGED = "task_status_changed"
    TASK_DUE_SOON = "task_due_soon"
    TASK_OVERDUE = "task_overdue"
    TASK_COMMENT = "task_comment"
    TASK_MENTION = "task_mention"
    
    # Document events
    DOCUMENT_APPROVAL_REQUESTED = "document_approval_requested"
    DOCUMENT_APPROVED = "document_approved"
    DOCUMENT_REJECTED = "document_rejected"
    DOCUMENT_STATUS_CHANGED = "document_status_changed"
    
    # Project events
    PROJECT_MEMBER_ADDED = "project_member_added"
    PROJECT_MEMBER_REMOVED = "project_member_removed"
    PROJECT_STATUS_CHANGED = "project_status_changed"
    PROJECT_MILESTONE_REACHED = "project_milestone_reached"
    
    # Budget events
    BUDGET_FIFTY_PERCENT = "budget_fifty_percent"
    BUDGET_WARNING = "budget_warning"
    BUDGET_EXCEEDED = "budget_exceeded"
    BUDGET_LOCKED = "budget_locked"
    
    # Approval workflow events
    APPROVAL_REQUESTED = "approval_requested"
    APPROVAL_APPROVED = "approval_approved"
    APPROVAL_REJECTED = "approval_rejected"
    
    # System events
    SYSTEM_ANNOUNCEMENT = "system_announcement"
    WEEKLY_DIGEST = "weekly_digest"


class NotificationChannel(str, Enum):
    """Notification delivery channels"""
    IN_APP = "in_app"
    EMAIL = "email"
    BROWSER_PUSH = "browser_push"


class NotificationPreferenceCreate(BaseModel):
    """Create notification preferences"""
    notification_type: NotificationType
    channels: List[NotificationChannel] = [NotificationChannel.IN_APP]
    enabled: bool = True


class NotificationPreferencesUpdate(BaseModel):
    """Update all notification preferences"""
    preferences: Dict[str, Dict] = Field(default_factory=dict)
    
    # Global settings
    email_notifications_enabled: bool = True
    browser_push_enabled: bool = False
    quiet_hours_enabled: bool = False
    quiet_hours_start: Optional[str] = "22:00"
    quiet_hours_end: Optional[str] = "08:00"
    
    @validator('quiet_hours_start', 'quiet_hours_end')
    def validate_time_format(cls, v):
        if v:
            try:
                datetime.strptime(v, "%H:%M")
            except ValueError:
                raise ValueError("Time must be in HH:MM format")
        return v


class NotificationPreferencesResponse(BaseModel):
    """Response for notification preferences"""
    user_id: str
    email_notifications_enabled: bool = True
    browser_push_enabled: bool = False
    quiet_hours_enabled: bool = False
    quiet_hours_start: Optional[str] = "22:00"
    quiet_hours_end: Optional[str] = "08:00"
    preferences: Dict[str, Dict] = Field(default_factory=dict)
    updated_at: Optional[str] = None


class NotificationCreate(BaseModel):
    """Create a notification"""
    user_id: str
    type: NotificationType
    title: str
    message: str
    link: Optional[str] = None
    metadata: Optional[Dict] = None
    
    @validator('title')
    def title_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("Title cannot be empty")
        return v.strip()
    
    @validator('message')
    def message_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("Message cannot be empty")
        return v.strip()


class NotificationResponse(BaseModel):
    """Response for a single notification"""
    notification_id: str
    user_id: str
    type: str
    title: str
    message: str
    link: Optional[str] = None
    metadata: Optional[Dict] = None
    read: bool = False
    read_at: Optional[str] = None
    created_at: str


class NotificationListResponse(BaseModel):
    """Paginated notification list response"""
    notifications: List[NotificationResponse]
    total: int
    page: int
    page_size: int
    has_more: bool


# Default notification preferences template
DEFAULT_NOTIFICATION_PREFERENCES = {
    # Task events
    NotificationType.TASK_ASSIGNED.value: {
        "enabled": True,
        "channels": [NotificationChannel.IN_APP.value, NotificationChannel.EMAIL.value]
    },
    NotificationType.TASK_STATUS_CHANGED.value: {
        "enabled": True,
        "channels": [NotificationChannel.IN_APP.value]
    },
    NotificationType.TASK_DUE_SOON.value: {
        "enabled": True,
        "channels": [NotificationChannel.IN_APP.value, NotificationChannel.EMAIL.value]
    },
    NotificationType.TASK_OVERDUE.value: {
        "enabled": True,
        "channels": [NotificationChannel.IN_APP.value, NotificationChannel.EMAIL.value]
    },
    NotificationType.TASK_COMMENT.value: {
        "enabled": True,
        "channels": [NotificationChannel.IN_APP.value]
    },
    NotificationType.TASK_MENTION.value: {
        "enabled": True,
        "channels": [NotificationChannel.IN_APP.value, NotificationChannel.EMAIL.value]
    },
    
    # Document events
    NotificationType.DOCUMENT_APPROVAL_REQUESTED.value: {
        "enabled": True,
        "channels": [NotificationChannel.IN_APP.value, NotificationChannel.EMAIL.value]
    },
    NotificationType.DOCUMENT_APPROVED.value: {
        "enabled": True,
        "channels": [NotificationChannel.IN_APP.value, NotificationChannel.EMAIL.value]
    },
    NotificationType.DOCUMENT_REJECTED.value: {
        "enabled": True,
        "channels": [NotificationChannel.IN_APP.value, NotificationChannel.EMAIL.value]
    },
    NotificationType.DOCUMENT_STATUS_CHANGED.value: {
        "enabled": True,
        "channels": [NotificationChannel.IN_APP.value]
    },
    
    # Project events
    NotificationType.PROJECT_MEMBER_ADDED.value: {
        "enabled": True,
        "channels": [NotificationChannel.IN_APP.value, NotificationChannel.EMAIL.value]
    },
    NotificationType.PROJECT_MEMBER_REMOVED.value: {
        "enabled": True,
        "channels": [NotificationChannel.IN_APP.value, NotificationChannel.EMAIL.value]
    },
    NotificationType.PROJECT_STATUS_CHANGED.value: {
        "enabled": True,
        "channels": [NotificationChannel.IN_APP.value]
    },
    NotificationType.PROJECT_MILESTONE_REACHED.value: {
        "enabled": True,
        "channels": [NotificationChannel.IN_APP.value, NotificationChannel.EMAIL.value]
    },
    
    # Approval workflow events
    NotificationType.APPROVAL_REQUESTED.value: {
        "enabled": True,
        "channels": [NotificationChannel.IN_APP.value, NotificationChannel.EMAIL.value]
    },
    NotificationType.APPROVAL_APPROVED.value: {
        "enabled": True,
        "channels": [NotificationChannel.IN_APP.value, NotificationChannel.EMAIL.value]
    },
    NotificationType.APPROVAL_REJECTED.value: {
        "enabled": True,
        "channels": [NotificationChannel.IN_APP.value, NotificationChannel.EMAIL.value]
    },
    
    # System events
    NotificationType.SYSTEM_ANNOUNCEMENT.value: {
        "enabled": True,
        "channels": [NotificationChannel.IN_APP.value, NotificationChannel.EMAIL.value]
    },
    NotificationType.WEEKLY_DIGEST.value: {
        "enabled": False,
        "channels": [NotificationChannel.EMAIL.value]
    },
}
