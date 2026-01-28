"""Customer-related models"""
from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime

class CustomerCreate(BaseModel):
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    company: Optional[str] = None
    address: Optional[str] = None
    notes: Optional[str] = None

class CustomerUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    company: Optional[str] = None
    address: Optional[str] = None
    notes: Optional[str] = None

class CustomerResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    customer_id: str
    org_id: str
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    company: Optional[str] = None
    address: Optional[str] = None
    notes: Optional[str] = None
    project_count: int = 0
    created_at: datetime
    updated_at: datetime
