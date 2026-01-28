"""Comment-related models with validation"""
from pydantic import BaseModel, ConfigDict, field_validator
from typing import Optional, List
from datetime import datetime


class CommentCreate(BaseModel):
    """Model for creating a comment"""
    content: str
    task_id: Optional[str] = None
    project_id: Optional[str] = None
    mentions: List[str] = []
    
    @field_validator('content')
    @classmethod
    def content_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError('Comment content cannot be empty')
        if len(v) > 10000:
            raise ValueError('Comment content cannot exceed 10000 characters')
        return v.strip()
    
    @field_validator('task_id', 'project_id')
    @classmethod
    def validate_parent_id(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and len(v) > 100:
            raise ValueError('Invalid ID format')
        return v
    
    @field_validator('mentions')
    @classmethod
    def validate_mentions(cls, v: List[str]) -> List[str]:
        if len(v) > 50:
            raise ValueError('Cannot mention more than 50 users')
        return v


class CommentUpdate(BaseModel):
    """Model for updating a comment"""
    content: str
    
    @field_validator('content')
    @classmethod
    def content_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError('Comment content cannot be empty')
        if len(v) > 10000:
            raise ValueError('Comment content cannot exceed 10000 characters')
        return v.strip()


class CommentResponse(BaseModel):
    """Response model for comments"""
    model_config = ConfigDict(extra="ignore")
    
    comment_id: str
    content: str
    task_id: Optional[str] = None
    project_id: Optional[str] = None
    author_id: str
    author_name: str
    author_picture: Optional[str] = None
    mentions: List[str] = []
    created_at: datetime
    updated_at: datetime
