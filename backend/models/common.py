"""Common models used across multiple modules"""
from pydantic import BaseModel, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime

class CommentCreate(BaseModel):
    task_id: str
    content: str
    mentions: List[str] = []

class CommentResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    comment_id: str
    task_id: str
    user_id: str
    user_name: str
    user_picture: Optional[str] = None
    content: str
    mentions: List[str] = []
    created_at: datetime

class TimeEntryCreate(BaseModel):
    task_id: str
    duration_minutes: int
    description: Optional[str] = None
    date: Optional[str] = None

class TimeEntryResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    entry_id: str
    task_id: str
    user_id: str
    duration_minutes: int
    description: Optional[str] = None
    date: str
    created_at: datetime

class TimerStart(BaseModel):
    task_id: str
    description: Optional[str] = None

class TimerResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    timer_id: str
    task_id: str
    user_id: str
    description: Optional[str] = None
    started_at: datetime
    running: bool = True

class NotificationResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    notification_id: str
    user_id: str
    type: str
    title: str
    message: str
    link: Optional[str] = None
    read: bool = False
    created_at: datetime

class AttachmentResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    attachment_id: str
    task_id: str
    filename: str
    original_filename: str
    content_type: str
    size: int
    uploaded_by: str
    created_at: datetime

class SearchResult(BaseModel):
    model_config = ConfigDict(extra="ignore")
    type: str
    id: str
    title: str
    description: Optional[str] = None
    project_id: Optional[str] = None
    project_name: Optional[str] = None
    status: Optional[str] = None
