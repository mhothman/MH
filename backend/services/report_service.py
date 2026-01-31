"""Report Service - Business logic for report generation and calculations"""
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
import logging

from core.database import get_database

logger = logging.getLogger(__name__)


class ReportService:
    """Service for generating reports and analytics"""
    
    @staticmethod
    async def get_executive_summary(org_id: str) -> Dict[str, Any]:
        """Generate executive dashboard summary"""
        db = get_database()
        
        # Get all projects for org
        projects = await db.projects.find({"org_id": org_id}, {"_id": 0}).to_list(500)
        project_ids = [p["project_id"] for p in projects]
        
        if not project_ids:
            return ReportService._empty_executive_summary()
        
        # Get task metrics using aggregation
        task_stats = await db.tasks.aggregate([
            {"$match": {"project_id": {"$in": project_ids}}},
            {"$group": {
                "_id": None,
                "total": {"$sum": 1},
                "completed": {"$sum": {"$cond": [{"$eq": ["$status", "done"]}, 1, 0]}},
                "in_progress": {"$sum": {"$cond": [{"$eq": ["$status", "in_progress"]}, 1, 0]}},
                "todo": {"$sum": {"$cond": [{"$eq": ["$status", "todo"]}, 1, 0]}},
                "high_priority": {"$sum": {"$cond": [{"$eq": ["$priority", "high"]}, 1, 0]}},
                "total_estimated": {"$sum": {"$ifNull": ["$estimated_hours", 0]}},
                "total_actual": {"$sum": {"$ifNull": ["$actual_hours", 0]}}
            }}
        ]).to_list(1)
        
        stats = task_stats[0] if task_stats else {
            "total": 0, "completed": 0, "in_progress": 0, "todo": 0,
            "high_priority": 0, "total_estimated": 0, "total_actual": 0
        }
        
        # Calculate overdue tasks
        now = datetime.now(timezone.utc).isoformat()
        overdue_count = await db.tasks.count_documents({
            "project_id": {"$in": project_ids},
            "due_date": {"$lt": now},
            "status": {"$ne": "done"}
        })
        
        # Project status breakdown
        project_stats = {
            "total": len(projects),
            "active": len([p for p in projects if p.get("status") == "active"]),
            "completed": len([p for p in projects if p.get("status") == "completed"]),
            "on_hold": len([p for p in projects if p.get("status") == "on_hold"])
        }
        
        return {
            "tasks": {
                "total": stats["total"],
                "completed": stats["completed"],
                "in_progress": stats["in_progress"],
                "todo": stats["todo"],
                "overdue": overdue_count,
                "high_priority": stats["high_priority"],
                "completion_rate": round(stats["completed"] / stats["total"] * 100, 1) if stats["total"] > 0 else 0
            },
            "projects": project_stats,
            "hours": {
                "estimated": round(stats["total_estimated"], 1),
                "actual": round(stats["total_actual"], 1),
                "variance": round(stats["total_actual"] - stats["total_estimated"], 1)
            }
        }
    
    @staticmethod
    def _empty_executive_summary() -> Dict[str, Any]:
        """Return empty summary structure"""
        return {
            "tasks": {"total": 0, "completed": 0, "in_progress": 0, "todo": 0, "overdue": 0, "high_priority": 0, "completion_rate": 0},
            "projects": {"total": 0, "active": 0, "completed": 0, "on_hold": 0},
            "hours": {"estimated": 0, "actual": 0, "variance": 0}
        }
    
    @staticmethod
    async def get_workload_distribution(org_id: str) -> List[Dict[str, Any]]:
        """Get workload distribution by team member"""
        db = get_database()
        
        # Get org members
        memberships = await db.org_memberships.find({"org_id": org_id}, {"_id": 0}).to_list(100)
        user_ids = [m["user_id"] for m in memberships]
        
        # Get users
        users = await db.users.find({"user_id": {"$in": user_ids}}, {"_id": 0, "user_id": 1, "name": 1, "picture": 1}).to_list(100)
        user_map = {u["user_id"]: u for u in users}
        
        # Get projects for org
        projects = await db.projects.find({"org_id": org_id}, {"project_id": 1}).to_list(500)
        project_ids = [p["project_id"] for p in projects]
        
        # Get task assignments using aggregation
        workload = await db.tasks.aggregate([
            {"$match": {"project_id": {"$in": project_ids}}},
            {"$unwind": "$assignee_ids"},
            {"$group": {
                "_id": "$assignee_ids",
                "total_tasks": {"$sum": 1},
                "completed": {"$sum": {"$cond": [{"$eq": ["$status", "done"]}, 1, 0]}},
                "in_progress": {"$sum": {"$cond": [{"$eq": ["$status", "in_progress"]}, 1, 0]}},
                "estimated_hours": {"$sum": {"$ifNull": ["$estimated_hours", 0]}},
                "actual_hours": {"$sum": {"$ifNull": ["$actual_hours", 0]}}
            }}
        ]).to_list(100)
        
        result = []
        for w in workload:
            user = user_map.get(w["_id"], {})
            result.append({
                "user_id": w["_id"],
                "name": user.get("name", "Unknown"),
                "picture": user.get("picture"),
                "total_tasks": w["total_tasks"],
                "completed": w["completed"],
                "in_progress": w["in_progress"],
                "estimated_hours": round(w["estimated_hours"], 1),
                "actual_hours": round(w["actual_hours"], 1),
                "completion_rate": round(w["completed"] / w["total_tasks"] * 100, 1) if w["total_tasks"] > 0 else 0
            })
        
        return sorted(result, key=lambda x: x["total_tasks"], reverse=True)
    
    @staticmethod
    async def get_productivity_trends(org_id: str, days: int = 30) -> Dict[str, Any]:
        """Get productivity trends over time"""
        db = get_database()
        
        # Get projects for org
        projects = await db.projects.find({"org_id": org_id}, {"project_id": 1}).to_list(500)
        project_ids = [p["project_id"] for p in projects]
        
        if not project_ids:
            return {"daily_completions": [], "cumulative": [], "average_per_day": 0}
        
        # Calculate date range
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days)
        
        # Get tasks completed in date range
        tasks = await db.tasks.find({
            "project_id": {"$in": project_ids},
            "status": "done",
            "updated_at": {"$gte": start_date.isoformat()}
        }, {"_id": 0, "updated_at": 1}).to_list(2000)
        
        # Group by day
        daily_counts = {}
        for task in tasks:
            date_str = task["updated_at"][:10]  # Extract YYYY-MM-DD
            daily_counts[date_str] = daily_counts.get(date_str, 0) + 1
        
        # Build daily series
        daily_completions = []
        cumulative = []
        running_total = 0
        
        current = start_date
        while current <= end_date:
            date_str = current.strftime("%Y-%m-%d")
            count = daily_counts.get(date_str, 0)
            running_total += count
            
            daily_completions.append({"date": date_str, "count": count})
            cumulative.append({"date": date_str, "total": running_total})
            
            current += timedelta(days=1)
        
        return {
            "daily_completions": daily_completions,
            "cumulative": cumulative,
            "average_per_day": round(running_total / days, 2) if days > 0 else 0,
            "total_completed": running_total
        }
    
    @staticmethod
    async def get_project_health(project_id: str) -> Dict[str, Any]:
        """Get health metrics for a specific project"""
        db = get_database()
        
        project = await db.projects.find_one({"project_id": project_id}, {"_id": 0})
        if not project:
            return {"error": "Project not found"}
        
        # Get task stats
        task_stats = await db.tasks.aggregate([
            {"$match": {"project_id": project_id}},
            {"$group": {
                "_id": None,
                "total": {"$sum": 1},
                "completed": {"$sum": {"$cond": [{"$eq": ["$status", "done"]}, 1, 0]}},
                "in_progress": {"$sum": {"$cond": [{"$eq": ["$status", "in_progress"]}, 1, 0]}},
                "estimated_hours": {"$sum": {"$ifNull": ["$estimated_hours", 0]}},
                "actual_hours": {"$sum": {"$ifNull": ["$actual_hours", 0]}}
            }}
        ]).to_list(1)
        
        stats = task_stats[0] if task_stats else {"total": 0, "completed": 0, "in_progress": 0, "estimated_hours": 0, "actual_hours": 0}
        
        # Calculate overdue
        now = datetime.now(timezone.utc).isoformat()
        overdue = await db.tasks.count_documents({
            "project_id": project_id,
            "due_date": {"$lt": now},
            "status": {"$ne": "done"}
        })
        
        # Calculate health score (0-100)
        completion_rate = stats["completed"] / stats["total"] * 100 if stats["total"] > 0 else 0
        overdue_rate = overdue / stats["total"] * 100 if stats["total"] > 0 else 0
        
        health_score = max(0, min(100, completion_rate - (overdue_rate * 2)))
        
        health_status = "healthy" if health_score >= 70 else "at_risk" if health_score >= 40 else "critical"
        
        return {
            "project_id": project_id,
            "name": project.get("name"),
            "health_score": round(health_score, 1),
            "health_status": health_status,
            "tasks": {
                "total": stats["total"],
                "completed": stats["completed"],
                "in_progress": stats["in_progress"],
                "overdue": overdue
            },
            "hours": {
                "estimated": round(stats["estimated_hours"], 1),
                "actual": round(stats["actual_hours"], 1)
            },
            "completion_rate": round(completion_rate, 1)
        }
    
    @staticmethod
    async def get_time_tracking_summary(org_id: str, user_id: Optional[str] = None, days: int = 30) -> Dict[str, Any]:
        """Get time tracking summary"""
        db = get_database()
        
        # Get projects for org
        projects = await db.projects.find({"org_id": org_id}, {"project_id": 1}).to_list(500)
        project_ids = [p["project_id"] for p in projects]
        
        # Get tasks for projects
        tasks = await db.tasks.find({"project_id": {"$in": project_ids}}, {"task_id": 1}).to_list(2000)
        task_ids = [t["task_id"] for t in tasks]
        
        # Build time entry query
        start_date = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        query = {
            "task_id": {"$in": task_ids},
            "start_time": {"$gte": start_date}
        }
        if user_id:
            query["user_id"] = user_id
        
        # Get time entries
        entries = await db.time_entries.find(query, {"_id": 0}).to_list(2000)
        
        # Calculate totals
        total_minutes = sum(e.get("duration_minutes", 0) for e in entries)
        billable_minutes = sum(e.get("duration_minutes", 0) for e in entries if e.get("billable", True))
        
        # Group by day
        daily_hours = {}
        for entry in entries:
            date_str = entry["start_time"][:10]
            daily_hours[date_str] = daily_hours.get(date_str, 0) + entry.get("duration_minutes", 0) / 60
        
        return {
            "total_hours": round(total_minutes / 60, 2),
            "billable_hours": round(billable_minutes / 60, 2),
            "entries_count": len(entries),
            "average_per_day": round(total_minutes / 60 / days, 2) if days > 0 else 0,
            "daily_breakdown": [{"date": k, "hours": round(v, 2)} for k, v in sorted(daily_hours.items())]
        }
    
    # =============================================
    # Pagination Helpers
    # =============================================
    
    @staticmethod
    async def get_paginated_projects(
        org_id: str,
        page: int = 1,
        page_size: int = 20,
        status: str = None,
        search: str = None
    ) -> Dict[str, Any]:
        """Get paginated projects for an organization"""
        db = get_database()
        
        query = {"org_id": org_id}
        if status:
            query["status"] = status
        if search:
            query["name"] = {"$regex": search, "$options": "i"}
        
        total = await db.projects.count_documents(query)
        skip = (page - 1) * page_size
        total_pages = (total + page_size - 1) // page_size
        
        projects = await db.projects.find(query, {"_id": 0}).sort("created_at", -1).skip(skip).limit(page_size).to_list(page_size)
        
        # Enrich with task counts
        if projects:
            project_ids = [p["project_id"] for p in projects]
            task_counts = await db.tasks.aggregate([
                {"$match": {"project_id": {"$in": project_ids}}},
                {"$group": {
                    "_id": "$project_id",
                    "total": {"$sum": 1},
                    "completed": {"$sum": {"$cond": [{"$eq": ["$status", "done"]}, 1, 0]}}
                }}
            ]).to_list(100)
            
            task_counts_map = {tc["_id"]: tc for tc in task_counts}
            
            for project in projects:
                counts = task_counts_map.get(project["project_id"], {"total": 0, "completed": 0})
                project["task_count"] = counts["total"]
                project["completed_tasks"] = counts["completed"]
        
        return {
            "data": projects,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total": total,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_prev": page > 1
            }
        }
    
    @staticmethod
    async def get_paginated_tasks(
        org_id: str,
        page: int = 1,
        page_size: int = 20,
        project_id: str = None,
        status: str = None,
        priority: str = None,
        assignee_id: str = None,
        overdue_only: bool = False,
        search: str = None
    ) -> Dict[str, Any]:
        """Get paginated tasks for an organization"""
        db = get_database()
        
        # Get project IDs
        if project_id:
            project_ids = [project_id]
        else:
            projects = await db.projects.find({"org_id": org_id}, {"project_id": 1}).to_list(500)
            project_ids = [p["project_id"] for p in projects]
        
        query = {"project_id": {"$in": project_ids}}
        if status:
            query["status"] = status
        if priority:
            query["priority"] = priority
        if assignee_id:
            query["assignee_ids"] = assignee_id
        if search:
            query["title"] = {"$regex": search, "$options": "i"}
        if overdue_only:
            query["due_date"] = {"$lt": datetime.now(timezone.utc).isoformat()}
            query["status"] = {"$ne": "done"}
        
        total = await db.tasks.count_documents(query)
        skip = (page - 1) * page_size
        total_pages = (total + page_size - 1) // page_size
        
        tasks = await db.tasks.find(query, {"_id": 0}).sort("created_at", -1).skip(skip).limit(page_size).to_list(page_size)
        
        return {
            "data": tasks,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total": total,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_prev": page > 1
            }
        }
    
    @staticmethod
    async def get_resource_utilization(org_id: str) -> List[Dict[str, Any]]:
        """Get resource utilization metrics"""
        db = get_database()
        
        # Get all members
        members = await db.org_memberships.find({"org_id": org_id}, {"_id": 0}).to_list(None)
        user_ids = [m["user_id"] for m in members]
        
        # Batch fetch all users
        users_list = await db.users.find(
            {"user_id": {"$in": user_ids}}, 
            {"_id": 0, "user_id": 1, "name": 1}
        ).to_list(None)
        users_map = {u["user_id"]: u for u in users_list}
        
        # Get projects and tasks
        projects = await db.projects.find({"org_id": org_id}, {"_id": 0}).to_list(None)
        project_ids = [p["project_id"] for p in projects]
        
        tasks = await db.tasks.find({
            "project_id": {"$in": project_ids},
            "status": {"$ne": "done"}
        }, {"_id": 0}).to_list(None)
        
        # Batch fetch all time entries
        all_task_ids = [t["task_id"] for t in tasks]
        all_time_entries = await db.time_entries.find({
            "task_id": {"$in": all_task_ids}
        }, {"_id": 0, "user_id": 1, "task_id": 1, "duration_minutes": 1}).to_list(None)
        
        # Group time entries by user_id
        time_entries_by_user = {}
        for entry in all_time_entries:
            uid = entry.get("user_id")
            if uid not in time_entries_by_user:
                time_entries_by_user[uid] = []
            time_entries_by_user[uid].append(entry)
        
        # Calculate utilization per member
        utilization = []
        for user_id in user_ids:
            user_doc = users_map.get(user_id)
            user_tasks = [t for t in tasks if user_id in t.get("assignee_ids", [])]
            
            total_estimated = sum(t.get("estimated_hours", 0) or 0 for t in user_tasks)
            
            user_task_ids = {t["task_id"] for t in user_tasks}
            time_entries = [e for e in time_entries_by_user.get(user_id, []) if e.get("task_id") in user_task_ids]
            
            actual_hours = sum(e.get("duration_minutes", 0) for e in time_entries) / 60
            
            utilization.append({
                "user_id": user_id,
                "name": user_doc.get("name", "Unknown") if user_doc else "Unknown",
                "active_tasks": len(user_tasks),
                "estimated_hours": round(total_estimated, 1),
                "actual_hours": round(actual_hours, 1),
                "utilization_rate": round(actual_hours / max(total_estimated, 1) * 100, 1) if total_estimated > 0 else 0
            })
        
        utilization.sort(key=lambda x: x["active_tasks"], reverse=True)
        return utilization


# Singleton instance
report_service = ReportService()

    
    async def generate_time_tracking_report(
        self,
        org_id: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        project_ids: Optional[List[str]] = None,
        user_ids: Optional[List[str]] = None,
        group_by: str = "project"
    ) -> Dict[str, Any]:
        """Generate time tracking report"""
        db = get_database()
        
        query = {}
        if start_date:
            query["date"] = {"$gte": start_date}
        if end_date:
            if "date" in query:
                query["date"]["$lte"] = end_date
            else:
                query["date"] = {"$lte": end_date}
        if project_ids:
            tasks = await db.tasks.find(
                {"project_id": {"$in": project_ids}},
                {"_id": 0, "task_id": 1}
            ).to_list(1000)
            query["task_id"] = {"$in": [t["task_id"] for t in tasks]}
        if user_ids:
            query["user_id"] = {"$in": user_ids}
        
        entries = await db.time_entries.find(query, {"_id": 0}).to_list(10000)
        
        if group_by == "project":
            task_ids = list(set(e["task_id"] for e in entries))
            tasks = await db.tasks.find(
                {"task_id": {"$in": task_ids}},
                {"_id": 0, "task_id": 1, "project_id": 1}
            ).to_list(len(task_ids))
            task_map = {t["task_id"]: t["project_id"] for t in tasks}
            
            project_ids_list = list(set(task_map.values()))
            projects = await db.projects.find(
                {"project_id": {"$in": project_ids_list}},
                {"_id": 0, "project_id": 1, "name": 1}
            ).to_list(len(project_ids_list))
            project_names = {p["project_id"]: p["name"] for p in projects}
            
            grouped = {}
            for entry in entries:
                proj_id = task_map.get(entry["task_id"])
                if proj_id:
                    if proj_id not in grouped:
                        grouped[proj_id] = {
                            "project_name": project_names.get(proj_id, "Unknown"),
                            "total_minutes": 0,
                            "entry_count": 0
                        }
                    grouped[proj_id]["total_minutes"] += entry.get("duration_minutes", 0)
                    grouped[proj_id]["entry_count"] += 1
            
            for g in grouped.values():
                g["total_hours"] = round(g["total_minutes"] / 60, 2)
            
            return {
                "grouped_data": list(grouped.values()),
                "total_hours": round(sum(e.get("duration_minutes", 0) for e in entries) / 60, 2)
            }
        
        return {"entries": entries, "total_hours": round(sum(e.get("duration_minutes", 0) for e in entries) / 60, 2)}
    
    async def generate_budget_summary_report(
        self,
        org_id: str,
        project_ids: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Generate budget summary report"""
        db = get_database()
        
        query = {"org_id": org_id}
        if project_ids:
            query["project_id"] = {"$in": project_ids}
        
        budgets = await db.project_budgets.find(query, {"_id": 0}).to_list(1000)
        
        project_ids_list = [b["project_id"] for b in budgets]
        if project_ids_list:
            projects = await db.projects.find(
                {"project_id": {"$in": project_ids_list}},
                {"_id": 0, "project_id": 1, "name": 1}
            ).to_list(len(project_ids_list))
            projects_map = {p["project_id"]: p["name"] for p in projects}
            
            for budget in budgets:
                budget["project_name"] = projects_map.get(budget["project_id"], "Unknown")
        
        total_budget = sum(b.get("total_budget", 0) for b in budgets)
        total_spent = sum(b.get("spent_amount", 0) for b in budgets)
        total_remaining = sum(b.get("remaining_amount", 0) for b in budgets)
        
        return {
            "budgets": budgets,
            "summary": {
                "total_budget": total_budget,
                "total_spent": total_spent,
                "total_remaining": total_remaining,
                "total_projects": len(budgets),
                "exceeded_count": len([b for b in budgets if b.get("status") == "exceeded"]),
                "warning_count": len([b for b in budgets if b.get("status") == "warning"]),
            }
        }
    
    async def generate_project_progress_report(
        self,
        org_id: str,
        project_ids: Optional[List[str]] = None,
        status_filter: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate project progress report"""
        db = get_database()
        
        query = {"org_id": org_id}
        if project_ids:
            query["project_id"] = {"$in": project_ids}
        if status_filter:
            query["status"] = status_filter
        
        projects = await db.projects.find(query, {"_id": 0}).to_list(1000)
        
        for project in projects:
            tasks = await db.tasks.find(
                {"project_id": project["project_id"]},
                {"_id": 0, "status": 1}
            ).to_list(1000)
            
            project["total_tasks"] = len(tasks)
            project["completed_tasks"] = len([t for t in tasks if t.get("status") == "done"])
            project["in_progress_tasks"] = len([t for t in tasks if t.get("status") == "in_progress"])
            project["todo_tasks"] = len([t for t in tasks if t.get("status") == "todo"])
            project["completion_rate"] = (
                (project["completed_tasks"] / project["total_tasks"] * 100) 
                if project["total_tasks"] > 0 else 0
            )
        
        return {
            "projects": projects,
            "summary": {
                "total_projects": len(projects),
                "avg_completion_rate": sum(p.get("completion_rate", 0) for p in projects) / len(projects) if projects else 0,
                "total_tasks": sum(p.get("total_tasks", 0) for p in projects),
                "total_completed": sum(p.get("completed_tasks", 0) for p in projects)
            }
        }

