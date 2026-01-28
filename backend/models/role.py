"""Role-related models with validation"""
from pydantic import BaseModel, ConfigDict, field_validator, Field
from typing import Optional, List
from datetime import datetime
import re

# Hex color pattern
HEX_COLOR_PATTERN = re.compile(r'^#[0-9A-Fa-f]{6}$')


class CustomRoleCreate(BaseModel):
    """Model for creating a custom role"""
    name: str = Field(..., min_length=1, max_length=50)
    description: Optional[str] = Field(None, max_length=200)
    permissions: List[str] = Field(default_factory=list)
    color: Optional[str] = Field(None)
    
    @field_validator('name')
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError('Role name cannot be empty')
        v = v.strip()
        if len(v) > 50:
            raise ValueError('Role name cannot exceed 50 characters')
        # Check for valid characters
        if not re.match(r'^[\w\s\-]+$', v):
            raise ValueError('Role name can only contain letters, numbers, spaces, underscores, and hyphens')
        return v
    
    @field_validator('description')
    @classmethod
    def validate_description(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and len(v) > 200:
            raise ValueError('Description cannot exceed 200 characters')
        return v
    
    @field_validator('permissions')
    @classmethod
    def validate_permissions(cls, v: List[str]) -> List[str]:
        if len(v) > 100:
            raise ValueError('Cannot assign more than 100 permissions')
        # Remove duplicates while preserving order
        seen = set()
        unique = []
        for perm in v:
            if perm not in seen:
                seen.add(perm)
                unique.append(perm)
        return unique
    
    @field_validator('color')
    @classmethod
    def validate_color(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not HEX_COLOR_PATTERN.match(v):
            raise ValueError('Invalid color format. Must be a valid hex color (e.g., #3B82F6)')
        return v.upper() if v else v


class CustomRoleUpdate(BaseModel):
    """Model for updating a custom role"""
    name: Optional[str] = Field(None, min_length=1, max_length=50)
    description: Optional[str] = Field(None, max_length=200)
    permissions: Optional[List[str]] = None
    color: Optional[str] = Field(None)
    
    @field_validator('name')
    @classmethod
    def name_not_empty(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            if not v.strip():
                raise ValueError('Role name cannot be empty')
            v = v.strip()
            if len(v) > 50:
                raise ValueError('Role name cannot exceed 50 characters')
            if not re.match(r'^[\w\s\-]+$', v):
                raise ValueError('Role name can only contain letters, numbers, spaces, underscores, and hyphens')
        return v
    
    @field_validator('description')
    @classmethod
    def validate_description(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and len(v) > 200:
            raise ValueError('Description cannot exceed 200 characters')
        return v
    
    @field_validator('permissions')
    @classmethod
    def validate_permissions(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        if v is not None:
            if len(v) > 100:
                raise ValueError('Cannot assign more than 100 permissions')
            # Remove duplicates while preserving order
            seen = set()
            unique = []
            for perm in v:
                if perm not in seen:
                    seen.add(perm)
                    unique.append(perm)
            return unique
        return v
    
    @field_validator('color')
    @classmethod
    def validate_color(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not HEX_COLOR_PATTERN.match(v):
            raise ValueError('Invalid color format. Must be a valid hex color (e.g., #3B82F6)')
        return v.upper() if v else v


class BuiltInRoleUpdate(BaseModel):
    """Model for updating built-in role permissions"""
    permissions: Optional[List[str]] = None
    description: Optional[str] = None
    color: Optional[str] = None
    
    @field_validator('description')
    @classmethod
    def validate_description(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and len(v) > 200:
            raise ValueError('Description cannot exceed 200 characters')
        return v
    
    @field_validator('permissions')
    @classmethod
    def validate_permissions(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        if v is not None:
            if len(v) > 100:
                raise ValueError('Cannot assign more than 100 permissions')
            # Remove duplicates
            return list(dict.fromkeys(v))
        return v
    
    @field_validator('color')
    @classmethod
    def validate_color(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not HEX_COLOR_PATTERN.match(v):
            raise ValueError('Invalid color format. Must be a valid hex color (e.g., #3B82F6)')
        return v.upper() if v else v


class RoleResponse(BaseModel):
    """Response model for roles"""
    model_config = ConfigDict(extra="ignore")
    
    role_id: str
    org_id: str
    name: str
    description: Optional[str] = None
    permissions: List[str] = []
    color: Optional[str] = None
    is_builtin: bool = False
    member_count: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
