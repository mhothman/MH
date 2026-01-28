"""User-related models"""
from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import Optional
from datetime import datetime

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: str
    organization_name: Optional[str] = None
    invitation_token: Optional[str] = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    user_id: str
    email: str
    name: str
    picture: Optional[str] = None
    role: str
    email_verified: bool = False
    suspended: bool = False
    created_at: datetime

class TokenResponse(BaseModel):
    access_token: str
    user: UserResponse

class UserUpdate(BaseModel):
    name: Optional[str] = None
    picture: Optional[str] = None
