"""Seasonal Employee Router - Manage temporary workers"""
from fastapi import APIRouter, HTTPException, Request
from typing import List
import logging

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.security import require_auth, require_permission, get_user_org_membership
from core.permissions import Permission
from models.seasonal_employee import (
    SeasonalEmployeeCreate,
    SeasonalEmployeeUpdate,
    SeasonalEmployeeResponse,
    SeasonalEmployeeProjectAssign,
    SeasonalEmployeeProjectUpdate,
    SeasonalEmployeeProjectResponse,
    AttendanceCreate,
    AttendanceUpdate,
    AttendanceResponse,
    SeasonalEmployeeCostSummary
)
from services.seasonal_employee_service import seasonal_employee_service

logger = logging.getLogger(__name__)
router = APIRouter()


# ==================== Employee CRUD ====================

@router.post("/", response_model=SeasonalEmployeeResponse)
async def create_seasonal_employee(data: SeasonalEmployeeCreate, request: Request, org_id: str):
    """Create a seasonal employee"""
    user = await require_permission(request, org_id, Permission.PROJECT_MANAGE_TEAM)
    
    # Get tenant_id from org
    from core.database import get_database
    db = get_database()
    org = await db.organizations.find_one({"org_id": org_id}, {"_id": 0, "tenant_id": 1})
    tenant_id = org.get("tenant_id", "tenant_default") if org else "tenant_default"
    
    try:
        employee = await seasonal_employee_service.create_employee(
            org_id=org_id,
            tenant_id=tenant_id,
            first_name=data.first_name,
            second_name=data.second_name,
            third_name=data.third_name,
            national_id=data.national_id,
            profession=data.profession,
            mobile_number=data.mobile_number,
            email=data.email,
            created_by=user["user_id"]
        )
        
        # Add stats
        employee["total_projects"] = 0
        employee["total_days_worked"] = 0
        employee["total_cost"] = 0
        
        return SeasonalEmployeeResponse(**employee)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/org/{org_id}", response_model=List[SeasonalEmployeeResponse])
async def get_organization_employees(org_id: str, request: Request):
    """Get all seasonal employees for an organization"""
    await require_permission(request, org_id, Permission.PROJECT_VIEW)
    
    employees = await seasonal_employee_service.get_organization_employees(org_id)
    return [SeasonalEmployeeResponse(**emp) for emp in employees]


@router.get("/{employee_id}", response_model=SeasonalEmployeeResponse)
async def get_employee(employee_id: str, request: Request):
    """Get seasonal employee details"""
    user = await require_auth(request)
    
    employee = await seasonal_employee_service.get_employee(employee_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    # Verify user has access to this org
    membership = await get_user_org_membership(user["user_id"], employee["org_id"])
    if not membership:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return SeasonalEmployeeResponse(**employee)


@router.put("/{employee_id}")
async def update_employee(employee_id: str, data: SeasonalEmployeeUpdate, request: Request):
    """Update seasonal employee"""
    user = await require_auth(request)
    
    employee = await seasonal_employee_service.get_employee(employee_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    await require_permission(request, employee["org_id"], Permission.PROJECT_MANAGE_TEAM)
    
    updates = data.model_dump(exclude_unset=True)
    success, message = await seasonal_employee_service.update_employee(
        employee_id=employee_id,
        updates=updates,
        updated_by=user["user_id"]
    )
    
    if not success:
        raise HTTPException(status_code=400, detail=message)
    
    return {"message": message}


@router.delete("/{employee_id}")
async def delete_employee(employee_id: str, request: Request):
    """Delete seasonal employee"""
    user = await require_auth(request)
    
    employee = await seasonal_employee_service.get_employee(employee_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    await require_permission(request, employee["org_id"], Permission.PROJECT_MANAGE_TEAM)
    
    success, message = await seasonal_employee_service.delete_employee(
        employee_id=employee_id,
        deleted_by=user["user_id"]
    )
    
    if not success:
        raise HTTPException(status_code=400, detail=message)
    
    return {"message": message}


# ==================== Project Assignments ====================

@router.post("/assignments", response_model=SeasonalEmployeeProjectResponse)
async def assign_to_project(data: SeasonalEmployeeProjectAssign, request: Request):
    """Assign seasonal employee to a project"""
    user = await require_auth(request)
    
    # Get employee to verify org access
    employee = await seasonal_employee_service.get_employee(data.seasonal_employee_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    await require_permission(request, employee["org_id"], Permission.PROJECT_MANAGE_TEAM)
    
    try:
        assignment = await seasonal_employee_service.assign_to_project(
            seasonal_employee_id=data.seasonal_employee_id,
            project_id=data.project_id,
            day_rate=data.day_rate,
            start_date=data.start_date,
            end_date=data.end_date,
            assigned_by=user["user_id"]
        )
        
        assignment["days_worked"] = 0
        assignment["total_cost"] = 0
        
        return SeasonalEmployeeProjectResponse(**assignment)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/assignments/employee/{employee_id}", response_model=List[SeasonalEmployeeProjectResponse])
async def get_employee_assignments(employee_id: str, request: Request):
    """Get all assignments for an employee"""
    user = await require_auth(request)
    
    employee = await seasonal_employee_service.get_employee(employee_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    membership = await get_user_org_membership(user["user_id"], employee["org_id"])
    if not membership:
        raise HTTPException(status_code=403, detail="Access denied")
    
    assignments = await seasonal_employee_service.get_employee_assignments(employee_id)
    return [SeasonalEmployeeProjectResponse(**a) for a in assignments]


@router.get("/assignments/project/{project_id}", response_model=List[SeasonalEmployeeProjectResponse])
async def get_project_seasonal_workers(project_id: str, request: Request):
    """Get all seasonal employees for a project"""
    user = await require_auth(request)
    
    from core.database import get_database
    db = get_database()
    project = await db.projects.find_one({"project_id": project_id}, {"_id": 0, "org_id": 1})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    await require_permission(request, project["org_id"], Permission.PROJECT_VIEW)
    
    assignments = await seasonal_employee_service.get_project_seasonal_workers(project_id)
    return [SeasonalEmployeeProjectResponse(**a) for a in assignments]


@router.delete("/assignments/{assignment_id}")
async def delete_assignment(assignment_id: str, request: Request):
    """Delete project assignment"""
    user = await require_auth(request)
    
    from core.database import get_database
    db = get_database()
    assignment = await db.seasonal_employee_projects.find_one(
        {"assignment_id": assignment_id},
        {"_id": 0, "seasonal_employee_id": 1}
    )
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")
    
    employee = await seasonal_employee_service.get_employee(assignment["seasonal_employee_id"])
    await require_permission(request, employee["org_id"], Permission.PROJECT_MANAGE_TEAM)
    
    success, message = await seasonal_employee_service.delete_assignment(
        assignment_id=assignment_id,
        deleted_by=user["user_id"]
    )
    
    if not success:
        raise HTTPException(status_code=400, detail=message)
    
    return {"message": message}


# ==================== Attendance ====================

@router.post("/attendance", response_model=AttendanceResponse)
async def record_attendance(data: AttendanceCreate, request: Request):
    """Record attendance for seasonal employee"""
    user = await require_auth(request)
    
    from core.database import get_database
    db = get_database()
    assignment = await db.seasonal_employee_projects.find_one(
        {"assignment_id": data.seasonal_employee_project_id},
        {"_id": 0, "seasonal_employee_id": 1}
    )
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")
    
    employee = await seasonal_employee_service.get_employee(assignment["seasonal_employee_id"])
    await require_permission(request, employee["org_id"], Permission.PROJECT_MANAGE_TEAM)
    
    try:
        attendance = await seasonal_employee_service.record_attendance(
            assignment_id=data.seasonal_employee_project_id,
            work_date=data.work_date,
            time_in=data.time_in,
            time_out=data.time_out,
            created_by=user["user_id"]
        )
        return AttendanceResponse(**attendance)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/attendance/assignment/{assignment_id}", response_model=List[AttendanceResponse])
async def get_assignment_attendance(assignment_id: str, request: Request):
    """Get attendance records for an assignment"""
    user = await require_auth(request)
    
    from core.database import get_database
    db = get_database()
    assignment = await db.seasonal_employee_projects.find_one(
        {"assignment_id": assignment_id},
        {"_id": 0, "seasonal_employee_id": 1}
    )
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")
    
    employee = await seasonal_employee_service.get_employee(assignment["seasonal_employee_id"])
    membership = await get_user_org_membership(user["user_id"], employee["org_id"])
    if not membership:
        raise HTTPException(status_code=403, detail="Access denied")
    
    attendance = await seasonal_employee_service.get_assignment_attendance(assignment_id)
    return [AttendanceResponse(**a) for a in attendance]


@router.put("/attendance/{attendance_id}")
async def update_attendance(attendance_id: str, data: AttendanceUpdate, request: Request):
    """Update attendance record"""
    user = await require_auth(request)
    
    from core.database import get_database
    db = get_database()
    attendance = await db.seasonal_attendance.find_one(
        {"attendance_id": attendance_id},
        {"_id": 0, "assignment_id": 1}
    )
    if not attendance:
        raise HTTPException(status_code=404, detail="Attendance not found")
    
    assignment = await db.seasonal_employee_projects.find_one(
        {"assignment_id": attendance["assignment_id"]},
        {"_id": 0, "seasonal_employee_id": 1}
    )
    
    employee = await seasonal_employee_service.get_employee(assignment["seasonal_employee_id"])
    await require_permission(request, employee["org_id"], Permission.PROJECT_MANAGE_TEAM)
    
    updates = data.model_dump(exclude_unset=True)
    success, message = await seasonal_employee_service.update_attendance(
        attendance_id=attendance_id,
        updates=updates,
        updated_by=user["user_id"]
    )
    
    if not success:
        raise HTTPException(status_code=400, detail=message)
    
    return {"message": message}


@router.delete("/attendance/{attendance_id}")
async def delete_attendance(attendance_id: str, request: Request):
    """Delete attendance record"""
    user = await require_auth(request)
    
    from core.database import get_database
    db = get_database()
    attendance = await db.seasonal_attendance.find_one(
        {"attendance_id": attendance_id},
        {"_id": 0, "assignment_id": 1}
    )
    if not attendance:
        raise HTTPException(status_code=404, detail="Attendance not found")
    
    assignment = await db.seasonal_employee_projects.find_one(
        {"assignment_id": attendance["assignment_id"]},
        {"_id": 0, "seasonal_employee_id": 1}
    )
    
    employee = await seasonal_employee_service.get_employee(assignment["seasonal_employee_id"])
    await require_permission(request, employee["org_id"], Permission.PROJECT_MANAGE_TEAM)
    
    success, message = await seasonal_employee_service.delete_attendance(
        attendance_id=attendance_id,
        deleted_by=user["user_id"]
    )
    
    if not success:
        raise HTTPException(status_code=400, detail=message)
    
    return {"message": message}


# ==================== Reporting ====================

@router.get("/{employee_id}/cost-summary", response_model=SeasonalEmployeeCostSummary)
async def get_employee_cost_summary(employee_id: str, request: Request):
    """Get cost summary for a seasonal employee"""
    user = await require_auth(request)
    
    employee = await seasonal_employee_service.get_employee(employee_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    membership = await get_user_org_membership(user["user_id"], employee["org_id"])
    if not membership:
        raise HTTPException(status_code=403, detail="Access denied")
    
    try:
        summary = await seasonal_employee_service.get_employee_cost_summary(employee_id)
        return SeasonalEmployeeCostSummary(**summary)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
