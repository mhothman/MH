"""Customer management router - Refactored to use Repository pattern"""
from fastapi import APIRouter, HTTPException, Request
from datetime import datetime, timezone
from typing import List
import logging

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.database import get_database
from core.security import require_auth, get_user_org_membership
from core.permissions import Permission, has_permission
from models.enums import UserRole
from models.customer import CustomerCreate, CustomerUpdate, CustomerResponse
from repositories.customer_repository import customer_repository
from repositories.project_repository import project_repository
from services.audit_service import audit_service

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/")
async def get_customers(request: Request, org_id: str = None):
    """Get all customers for an organization"""
    db = get_database()
    user = await require_auth(request)
    
    if org_id:
        membership = await get_user_org_membership(user["user_id"], org_id)
        if not membership:
            raise HTTPException(status_code=403, detail="Access denied")
        
        if not has_permission(membership["role"], Permission.CUSTOMER_VIEW):
            raise HTTPException(status_code=403, detail="Permission denied: cannot view customers")
        
        customers = await customer_repository.get_with_project_counts(org_id)
    else:
        memberships = await db.org_memberships.find({"user_id": user["user_id"]}, {"_id": 0}).to_list(100)
        org_ids = [m["org_id"] for m in memberships]
        customers = await customer_repository.find_all({"org_id": {"$in": org_ids}})
        
        # Add project counts for each customer
        for customer in customers:
            projects = await project_repository.find_by_customer(customer["customer_id"])
            customer["project_count"] = len(projects)
    
    # Format dates
    for customer in customers:
        customer["created_at"] = datetime.fromisoformat(customer["created_at"]) if isinstance(customer["created_at"], str) else customer["created_at"]
        customer["updated_at"] = datetime.fromisoformat(customer.get("updated_at", customer["created_at"])) if isinstance(customer.get("updated_at"), str) else customer.get("updated_at", customer["created_at"])
    
    return customers


@router.get("/{customer_id}")
async def get_customer(customer_id: str, request: Request):
    """Get customer by ID"""
    user = await require_auth(request)
    
    customer = await customer_repository.find_by_id(customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    membership = await get_user_org_membership(user["user_id"], customer["org_id"])
    if not membership:
        raise HTTPException(status_code=403, detail="Access denied")
    
    projects = await project_repository.find_by_customer(customer_id)
    customer["project_count"] = len(projects)
    customer["created_at"] = datetime.fromisoformat(customer["created_at"]) if isinstance(customer["created_at"], str) else customer["created_at"]
    customer["updated_at"] = datetime.fromisoformat(customer.get("updated_at", customer["created_at"])) if isinstance(customer.get("updated_at"), str) else customer.get("updated_at", customer["created_at"])
    
    return customer


@router.post("/")
async def create_customer(data: CustomerCreate, request: Request, org_id: str):
    """Create a new customer"""
    user = await require_auth(request)
    
    membership = await get_user_org_membership(user["user_id"], org_id)
    if not membership:
        raise HTTPException(status_code=403, detail="Access denied")
    
    if not has_permission(membership["role"], Permission.CUSTOMER_CREATE):
        raise HTTPException(status_code=403, detail="Permission denied: cannot create customers")
    
    customer_data = {
        "org_id": org_id,
        "name": data.name,
        "email": data.email,
        "phone": data.phone,
        "company": data.company,
        "address": data.address,
        "notes": data.notes,
    }
    
    customer = await customer_repository.create(customer_data)
    
    await audit_service.log(user["user_id"], org_id, "create", "customer", customer["customer_id"])
    
    customer["project_count"] = 0
    customer["created_at"] = datetime.fromisoformat(customer["created_at"])
    customer["updated_at"] = datetime.fromisoformat(customer["updated_at"])
    
    return customer


@router.put("/{customer_id}")
async def update_customer(customer_id: str, data: CustomerUpdate, request: Request):
    """Update a customer"""
    user = await require_auth(request)
    
    customer = await customer_repository.find_by_id(customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    membership = await get_user_org_membership(user["user_id"], customer["org_id"])
    if not membership:
        raise HTTPException(status_code=403, detail="Access denied")
    
    if not has_permission(membership["role"], Permission.CUSTOMER_EDIT):
        raise HTTPException(status_code=403, detail="Permission denied: cannot edit customers")
    
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    
    if update_data:
        await customer_repository.update(customer_id, update_data)
    
    await audit_service.log(user["user_id"], customer["org_id"], "update", "customer", customer_id)
    
    return await get_customer(customer_id, request)


@router.delete("/{customer_id}")
async def delete_customer(customer_id: str, request: Request):
    """Delete a customer"""
    user = await require_auth(request)
    
    customer = await customer_repository.find_by_id(customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    membership = await get_user_org_membership(user["user_id"], customer["org_id"])
    if not membership:
        raise HTTPException(status_code=403, detail="Access denied")
    
    if not has_permission(membership["role"], Permission.CUSTOMER_DELETE):
        raise HTTPException(status_code=403, detail="Permission denied: cannot delete customers")
    
    # Check if customer has projects
    projects = await project_repository.find_by_customer(customer_id)
    if len(projects) > 0:
        raise HTTPException(status_code=400, detail=f"Cannot delete customer with {len(projects)} associated projects")
    
    await customer_repository.delete(customer_id)
    
    await audit_service.log(user["user_id"], customer["org_id"], "delete", "customer", customer_id)
    
    return {"message": "Customer deleted successfully"}


@router.get("/{customer_id}/projects")
async def get_customer_projects(customer_id: str, request: Request):
    """Get projects for a customer"""
    user = await require_auth(request)
    
    customer = await customer_repository.find_by_id(customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    membership = await get_user_org_membership(user["user_id"], customer["org_id"])
    if not membership:
        raise HTTPException(status_code=403, detail="Access denied")
    
    projects = await project_repository.find_by_customer(customer_id)
    
    return projects
