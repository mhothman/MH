"""Seasonal Employee Service - Manage temporary workers"""
import logging
from datetime import datetime, timezone, time as dt_time
from typing import List, Dict, Optional, Tuple
from uuid import uuid4

from core.database import get_database
from services.audit_service import audit_service

logger = logging.getLogger(__name__)


class SeasonalEmployeeService:
    """Service for seasonal employee management"""
    
    # ==================== Employee CRUD ====================
    
    async def create_employee(
        self,
        org_id: str,
        tenant_id: str,
        first_name: str,
        second_name: str,
        third_name: str,
        national_id: str,
        profession: str,
        mobile_number: str,
        email: Optional[str],
        created_by: str
    ) -> Dict:
        """Create a seasonal employee"""
        db = get_database()
        
        # Check if national ID already exists in this organization
        existing = await db.seasonal_employees.find_one({
            "org_id": org_id,
            "national_id": national_id
        }, {"_id": 0})
        
        if existing:
            raise ValueError(f"National ID {national_id} already exists in this organization")
        
        employee_id = f"semp_{uuid4().hex[:12]}"
        now = datetime.now(timezone.utc).isoformat()
        
        employee = {
            "employee_id": employee_id,
            "tenant_id": tenant_id,
            "org_id": org_id,
            "first_name": first_name,
            "second_name": second_name,
            "third_name": third_name,
            "full_name": f"{first_name} {second_name} {third_name}",
            "national_id": national_id,
            "profession": profession,
            "mobile_number": mobile_number,
            "email": email,
            "created_at": now,
            "created_by": created_by
        }
        
        await db.seasonal_employees.insert_one(employee)
        employee.pop("_id", None)
        
        # Audit log
        await audit_service.log(
            org_id=org_id,
            user_id=created_by,
            action="seasonal_employee.create",
            resource_type="seasonal_employee",
            resource_id=employee_id,
            details={"name": employee["full_name"], "national_id": national_id}
        )
        
        logger.info(f"Seasonal employee created: {employee_id} ({employee['full_name']})")
        return employee
    
    async def get_employee(self, employee_id: str) -> Optional[Dict]:
        """Get seasonal employee by ID"""
        db = get_database()
        employee = await db.seasonal_employees.find_one({"employee_id": employee_id}, {"_id": 0})
        
        if employee:
            # Get stats
            employee["total_projects"] = await db.seasonal_employee_projects.count_documents({
                "seasonal_employee_id": employee_id
            })
            
            # Get total days worked
            assignments = await db.seasonal_employee_projects.find(
                {"seasonal_employee_id": employee_id},
                {"_id": 0, "assignment_id": 1}
            ).to_list(100)
            
            total_days = 0
            total_cost = 0
            for assignment in assignments:
                attendance_count = await db.seasonal_attendance.count_documents({
                    "assignment_id": assignment["assignment_id"]
                })
                total_days += attendance_count
                
                # Get assignment for cost calc
                assign_data = await db.seasonal_employee_projects.find_one(
                    {"assignment_id": assignment["assignment_id"]},
                    {"_id": 0, "day_rate": 1}
                )
                if assign_data:
                    total_cost += attendance_count * assign_data["day_rate"]
            
            employee["total_days_worked"] = total_days
            employee["total_cost"] = round(total_cost, 2)
        
        return employee
    
    async def get_organization_employees(self, org_id: str) -> List[Dict]:
        """Get all seasonal employees for an organization"""
        db = get_database()
        
        employees = await db.seasonal_employees.find(
            {"org_id": org_id},
            {"_id": 0}
        ).to_list(1000)
        
        # Get stats for each
        for emp in employees:
            emp["total_projects"] = await db.seasonal_employee_projects.count_documents({
                "seasonal_employee_id": emp["employee_id"]
            })
            
            # Quick stats (without detailed cost calc for list view)
            assignments = await db.seasonal_employee_projects.find(
                {"seasonal_employee_id": emp["employee_id"]},
                {"_id": 0, "assignment_id": 1}
            ).to_list(100)
            
            total_days = sum([
                await db.seasonal_attendance.count_documents({"assignment_id": a["assignment_id"]})
                for a in assignments
            ])
            emp["total_days_worked"] = total_days
        
        return employees
    
    async def update_employee(
        self,
        employee_id: str,
        updates: Dict,
        updated_by: str
    ) -> Tuple[bool, str]:
        """Update seasonal employee"""
        db = get_database()
        
        employee = await db.seasonal_employees.find_one({"employee_id": employee_id}, {"_id": 0})
        if not employee:
            return False, "Employee not found"
        
        # Update full_name if name fields changed
        if any(k in updates for k in ["first_name", "second_name", "third_name"]):
            first = updates.get("first_name", employee["first_name"])
            second = updates.get("second_name", employee["second_name"])
            third = updates.get("third_name", employee["third_name"])
            updates["full_name"] = f"{first} {second} {third}"
        
        updates["updated_at"] = datetime.now(timezone.utc).isoformat()
        
        await db.seasonal_employees.update_one(
            {"employee_id": employee_id},
            {"$set": updates}
        )
        
        # Audit log
        await audit_service.log(
            org_id=employee["org_id"],
            user_id=updated_by,
            action="seasonal_employee.update",
            resource_type="seasonal_employee",
            resource_id=employee_id,
            details=updates
        )
        
        return True, "Employee updated successfully"
    
    async def delete_employee(self, employee_id: str, deleted_by: str) -> Tuple[bool, str]:
        """Delete seasonal employee"""
        db = get_database()
        
        employee = await db.seasonal_employees.find_one({"employee_id": employee_id}, {"_id": 0})
        if not employee:
            return False, "Employee not found"
        
        # Get assignments
        assignments = await db.seasonal_employee_projects.find(
            {"seasonal_employee_id": employee_id},
            {"_id": 0, "assignment_id": 1}
        ).to_list(100)
        
        # Delete attendance records
        for assignment in assignments:
            await db.seasonal_attendance.delete_many({"assignment_id": assignment["assignment_id"]})
        
        # Delete assignments
        await db.seasonal_employee_projects.delete_many({"seasonal_employee_id": employee_id})
        
        # Delete employee
        await db.seasonal_employees.delete_one({"employee_id": employee_id})
        
        # Audit log
        await audit_service.log(
            org_id=employee["org_id"],
            user_id=deleted_by,
            action="seasonal_employee.delete",
            resource_type="seasonal_employee",
            resource_id=employee_id,
            details={"name": employee["full_name"], "assignments_deleted": len(assignments)}
        )
        
        logger.info(f"Seasonal employee deleted: {employee_id}")
        return True, "Employee deleted successfully"
    
    # ==================== Project Assignment ====================
    
    async def assign_to_project(
        self,
        seasonal_employee_id: str,
        project_id: str,
        day_rate: float,
        start_date: str,
        end_date: str,
        assigned_by: str
    ) -> Dict:
        """Assign seasonal employee to a project"""
        db = get_database()
        
        # Verify employee exists
        employee = await db.seasonal_employees.find_one(
            {"employee_id": seasonal_employee_id},
            {"_id": 0}
        )
        if not employee:
            raise ValueError("Employee not found")
        
        # Verify project exists
        project = await db.projects.find_one({"project_id": project_id}, {"_id": 0, "name": 1})
        if not project:
            raise ValueError("Project not found")
        
        # Validate dates
        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        end_dt = datetime.strptime(end_date, '%Y-%m-%d')
        if end_dt < start_dt:
            raise ValueError("End date must be after start date")
        
        assignment_id = f"sempassign_{uuid4().hex[:12]}"
        now = datetime.now(timezone.utc).isoformat()
        
        assignment = {
            "assignment_id": assignment_id,
            "seasonal_employee_id": seasonal_employee_id,
            "employee_name": employee["full_name"],
            "project_id": project_id,
            "project_name": project["name"],
            "day_rate": day_rate,
            "start_date": start_date,
            "end_date": end_date,
            "assigned_by": assigned_by,
            "created_at": now
        }
        
        await db.seasonal_employee_projects.insert_one(assignment)
        assignment.pop("_id", None)
        
        # Get assigned_by name
        assigner = await db.users.find_one({"user_id": assigned_by}, {"_id": 0, "name": 1})
        assignment["assigned_by_name"] = assigner["name"] if assigner else "Unknown"
        
        # Audit log
        await audit_service.log(
            org_id=employee["org_id"],
            user_id=assigned_by,
            action="seasonal_employee.assign_project",
            resource_type="seasonal_employee",
            resource_id=seasonal_employee_id,
            details={
                "project_id": project_id,
                "project_name": project["name"],
                "day_rate": day_rate,
                "period": f"{start_date} to {end_date}"
            }
        )
        
        logger.info(f"Seasonal employee {seasonal_employee_id} assigned to project {project_id}")
        return assignment
    
    async def get_employee_assignments(self, employee_id: str) -> List[Dict]:
        """Get all project assignments for an employee"""
        db = get_database()
        
        assignments = await db.seasonal_employee_projects.find(
            {"seasonal_employee_id": employee_id},
            {"_id": 0}
        ).to_list(100)
        
        # Get assigned_by names
        assigner_ids = list(set(a["assigned_by"] for a in assignments if a.get("assigned_by")))
        assigner_map = {}
        if assigner_ids:
            assigners = await db.users.find(
                {"user_id": {"$in": assigner_ids}},
                {"_id": 0, "user_id": 1, "name": 1}
            ).to_list(len(assigner_ids))
            assigner_map = {u["user_id"]: u["name"] for u in assigners}
        
        # Get days worked and cost for each
        for assignment in assignments:
            attendance_count = await db.seasonal_attendance.count_documents({
                "assignment_id": assignment["assignment_id"]
            })
            assignment["days_worked"] = attendance_count
            assignment["total_cost"] = round(attendance_count * assignment["day_rate"], 2)
            assignment["assigned_by_name"] = assigner_map.get(assignment.get("assigned_by"), "Unknown")
        
        return assignments
    
    async def get_project_seasonal_workers(self, project_id: str) -> List[Dict]:
        """Get all seasonal employees assigned to a project"""
        db = get_database()
        
        assignments = await db.seasonal_employee_projects.find(
            {"project_id": project_id},
            {"_id": 0}
        ).to_list(100)
        
        # Get assigned_by names
        assigner_ids = list(set(a["assigned_by"] for a in assignments if a.get("assigned_by")))
        assigner_map = {}
        if assigner_ids:
            assigners = await db.users.find(
                {"user_id": {"$in": assigner_ids}},
                {"_id": 0, "user_id": 1, "name": 1}
            ).to_list(len(assigner_ids))
            assigner_map = {u["user_id"]: u["name"] for u in assigners}
        
        for assignment in assignments:
            attendance_count = await db.seasonal_attendance.count_documents({
                "assignment_id": assignment["assignment_id"]
            })
            assignment["days_worked"] = attendance_count
            assignment["total_cost"] = round(attendance_count * assignment["day_rate"], 2)
            assignment["assigned_by_name"] = assigner_map.get(assignment.get("assigned_by"), "Unknown")
        
        return assignments
    
    async def update_assignment(
        self,
        assignment_id: str,
        updates: Dict,
        updated_by: str
    ) -> Tuple[bool, str]:
        """Update project assignment"""
        db = get_database()
        
        assignment = await db.seasonal_employee_projects.find_one(
            {"assignment_id": assignment_id},
            {"_id": 0}
        )
        if not assignment:
            return False, "Assignment not found"
        
        updates["updated_at"] = datetime.now(timezone.utc).isoformat()
        
        await db.seasonal_employee_projects.update_one(
            {"assignment_id": assignment_id},
            {"$set": updates}
        )
        
        return True, "Assignment updated successfully"
    
    async def delete_assignment(self, assignment_id: str, deleted_by: str) -> Tuple[bool, str]:
        """Delete project assignment"""
        db = get_database()
        
        assignment = await db.seasonal_employee_projects.find_one(
            {"assignment_id": assignment_id},
            {"_id": 0}
        )
        if not assignment:
            return False, "Assignment not found"
        
        # Delete attendance records
        await db.seasonal_attendance.delete_many({"assignment_id": assignment_id})
        
        # Delete assignment
        await db.seasonal_employee_projects.delete_one({"assignment_id": assignment_id})
        
        logger.info(f"Assignment deleted: {assignment_id}")
        return True, "Assignment deleted successfully"
    
    # ==================== Attendance Management ====================
    
    async def record_attendance(
        self,
        assignment_id: str,
        work_date: str,
        time_in: str,
        time_out: str,
        created_by: str
    ) -> Dict:
        """Record attendance for a seasonal employee"""
        db = get_database()
        
        # Verify assignment exists
        assignment = await db.seasonal_employee_projects.find_one(
            {"assignment_id": assignment_id},
            {"_id": 0}
        )
        if not assignment:
            raise ValueError("Assignment not found")
        
        # Validate work_date is within assignment period
        work_date_dt = datetime.strptime(work_date, '%Y-%m-%d').date()
        start_date_dt = datetime.strptime(assignment["start_date"], '%Y-%m-%d').date()
        end_date_dt = datetime.strptime(assignment["end_date"], '%Y-%m-%d').date()
        
        if work_date_dt < start_date_dt or work_date_dt > end_date_dt:
            raise ValueError(
                f"Work date must be within project period ({assignment['start_date']} to {assignment['end_date']})"
            )
        
        # Validate time_in < time_out
        time_in_dt = datetime.strptime(time_in, '%H:%M').time()
        time_out_dt = datetime.strptime(time_out, '%H:%M').time()
        if time_out_dt <= time_in_dt:
            raise ValueError("Time out must be after time in")
        
        # Calculate hours worked
        time_in_minutes = time_in_dt.hour * 60 + time_in_dt.minute
        time_out_minutes = time_out_dt.hour * 60 + time_out_dt.minute
        hours_worked = (time_out_minutes - time_in_minutes) / 60
        
        # Check if attendance already exists for this date
        existing = await db.seasonal_attendance.find_one({
            "assignment_id": assignment_id,
            "work_date": work_date
        }, {"_id": 0})
        
        if existing:
            raise ValueError(f"Attendance already recorded for {work_date}")
        
        attendance_id = f"sempatten_{uuid4().hex[:12]}"
        now = datetime.now(timezone.utc).isoformat()
        
        attendance = {
            "attendance_id": attendance_id,
            "assignment_id": assignment_id,
            "employee_name": assignment["employee_name"],
            "project_name": assignment["project_name"],
            "work_date": work_date,
            "time_in": time_in,
            "time_out": time_out,
            "hours_worked": round(hours_worked, 2),
            "created_by": created_by,
            "created_at": now
        }
        
        await db.seasonal_attendance.insert_one(attendance)
        attendance.pop("_id", None)
        
        # Get creator name
        creator = await db.users.find_one({"user_id": created_by}, {"_id": 0, "name": 1})
        attendance["created_by_name"] = creator["name"] if creator else "Unknown"
        
        logger.info(f"Attendance recorded: {attendance_id} for {work_date}")
        return attendance
    
    async def get_assignment_attendance(self, assignment_id: str) -> List[Dict]:
        """Get all attendance records for an assignment"""
        db = get_database()
        
        attendance = await db.seasonal_attendance.find(
            {"assignment_id": assignment_id},
            {"_id": 0}
        ).sort("work_date", -1).to_list(1000)
        
        # Get creator names
        creator_ids = list(set(a["created_by"] for a in attendance))
        if creator_ids:
            creators = await db.users.find(
                {"user_id": {"$in": creator_ids}},
                {"_id": 0, "user_id": 1, "name": 1}
            ).to_list(len(creator_ids))
            creator_map = {c["user_id"]: c["name"] for c in creators}
            
            for record in attendance:
                record["created_by_name"] = creator_map.get(record["created_by"], "Unknown")
        
        return attendance
    
    async def update_attendance(
        self,
        attendance_id: str,
        updates: Dict,
        updated_by: str
    ) -> Tuple[bool, str]:
        """Update attendance record"""
        db = get_database()
        
        attendance = await db.seasonal_attendance.find_one(
            {"attendance_id": attendance_id},
            {"_id": 0}
        )
        if not attendance:
            return False, "Attendance record not found"
        
        # Recalculate hours if times changed
        if "time_in" in updates or "time_out" in updates:
            time_in_str = updates.get("time_in", attendance["time_in"])
            time_out_str = updates.get("time_out", attendance["time_out"])
            
            time_in_dt = datetime.strptime(time_in_str, '%H:%M').time()
            time_out_dt = datetime.strptime(time_out_str, '%H:%M').time()
            
            if time_out_dt <= time_in_dt:
                return False, "Time out must be after time in"
            
            time_in_minutes = time_in_dt.hour * 60 + time_in_dt.minute
            time_out_minutes = time_out_dt.hour * 60 + time_out_dt.minute
            updates["hours_worked"] = round((time_out_minutes - time_in_minutes) / 60, 2)
        
        updates["updated_at"] = datetime.now(timezone.utc).isoformat()
        
        await db.seasonal_attendance.update_one(
            {"attendance_id": attendance_id},
            {"$set": updates}
        )
        
        return True, "Attendance updated successfully"
    
    async def delete_attendance(self, attendance_id: str, deleted_by: str) -> Tuple[bool, str]:
        """Delete attendance record"""
        db = get_database()
        
        attendance = await db.seasonal_attendance.find_one(
            {"attendance_id": attendance_id},
            {"_id": 0}
        )
        if not attendance:
            return False, "Attendance record not found"
        
        await db.seasonal_attendance.delete_one({"attendance_id": attendance_id})
        
        logger.info(f"Attendance deleted: {attendance_id}")
        return True, "Attendance record deleted successfully"
    
    # ==================== Reporting ====================
    
    async def get_employee_cost_summary(self, employee_id: str) -> Dict:
        """Get detailed cost summary for an employee"""
        db = get_database()
        
        employee = await self.get_employee(employee_id)
        if not employee:
            raise ValueError("Employee not found")
        
        assignments = await self.get_employee_assignments(employee_id)
        
        total_hours = 0
        for assignment in assignments:
            # Get attendance for hours
            attendance = await db.seasonal_attendance.find(
                {"assignment_id": assignment["assignment_id"]},
                {"_id": 0, "hours_worked": 1}
            ).to_list(1000)
            
            assignment_hours = sum(a.get("hours_worked", 0) for a in attendance)
            assignment["total_hours_worked"] = round(assignment_hours, 2)
            total_hours += assignment_hours
        
        return {
            "employee_id": employee_id,
            "employee_name": employee["full_name"],
            "total_projects": len(assignments),
            "total_days_worked": employee["total_days_worked"],
            "total_hours_worked": round(total_hours, 2),
            "total_cost": employee["total_cost"],
            "assignments": assignments
        }


# Singleton instance
seasonal_employee_service = SeasonalEmployeeService()
