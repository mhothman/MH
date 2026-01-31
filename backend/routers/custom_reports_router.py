"""Custom Reports Router - Advanced reporting with exports"""
from fastapi import APIRouter, HTTPException, Request, Query, Response
from fastapi.responses import StreamingResponse
from typing import Optional, List
from datetime import datetime, timezone
import io
import csv
import logging

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.security import require_auth, get_user_org_membership
from core.permissions import Permission, has_permission
from services.report_service import ReportService

logger = logging.getLogger(__name__)
router = APIRouter()
report_service = ReportService()


@router.get("/time-tracking")
async def get_time_tracking_report(
    request: Request,
    org_id: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    project_ids: Optional[str] = None,  # Comma-separated
    user_ids: Optional[str] = None,  # Comma-separated
    group_by: str = Query("project", regex="^(project|user|date)$"),
    export_format: Optional[str] = Query(None, regex="^(csv|json)$")
):
    """Generate time tracking report with optional export"""
    user = await require_auth(request)
    
    membership = await get_user_org_membership(user["user_id"], org_id)
    if not membership:
        raise HTTPException(status_code=403, detail="Access denied")
    
    if not has_permission(membership["role"], Permission.REPORT_VIEW):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    # Parse project_ids and user_ids
    project_list = project_ids.split(",") if project_ids else None
    user_list = user_ids.split(",") if user_ids else None
    
    # Generate report
    report_data = await report_service.generate_time_tracking_report(
        org_id=org_id,
        start_date=start_date,
        end_date=end_date,
        project_ids=project_list,
        user_ids=user_list,
        group_by=group_by
    )
    
    # Export if requested
    if export_format == "csv":
        return _export_to_csv(report_data, "time_tracking_report")
    
    return report_data


@router.get("/budget-summary")
async def get_budget_summary_report(
    request: Request,
    org_id: str,
    project_ids: Optional[str] = None,
    export_format: Optional[str] = Query(None, regex="^(csv|json)$")
):
    """Generate budget summary report with optional export"""
    user = await require_auth(request)
    
    membership = await get_user_org_membership(user["user_id"], org_id)
    if not membership:
        raise HTTPException(status_code=403, detail="Access denied")
    
    if not has_permission(membership["role"], Permission.BUDGET_VIEW):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    project_list = project_ids.split(",") if project_ids else None
    
    report_data = await report_service.generate_budget_summary_report(
        org_id=org_id,
        project_ids=project_list
    )
    
    if export_format == "csv":
        return _export_budget_to_csv(report_data)
    
    return report_data


@router.get("/project-progress")
async def get_project_progress_report(
    request: Request,
    org_id: str,
    project_ids: Optional[str] = None,
    status: Optional[str] = None,
    export_format: Optional[str] = Query(None, regex="^(csv)$")
):
    """Generate project progress report"""
    user = await require_auth(request)
    
    membership = await get_user_org_membership(user["user_id"], org_id)
    if not membership:
        raise HTTPException(status_code=403, detail="Access denied")
    
    if not has_permission(membership["role"], Permission.REPORT_VIEW):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    project_list = project_ids.split(",") if project_ids else None
    
    report_data = await report_service.generate_project_progress_report(
        org_id=org_id,
        project_ids=project_list,
        status_filter=status
    )
    
    if export_format == "csv":
        return _export_projects_to_csv(report_data)
    
    return report_data



@router.get("/task-completion")
async def get_task_completion_report(
    request: Request,
    org_id: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    project_ids: Optional[str] = None,
    export_format: Optional[str] = Query(None, regex="^(csv)$")
):
    """Generate task completion rates report"""
    user = await require_auth(request)
    
    membership = await get_user_org_membership(user["user_id"], org_id)
    if not membership:
        raise HTTPException(status_code=403, detail="Access denied")
    
    if not has_permission(membership["role"], Permission.REPORT_VIEW):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    project_list = project_ids.split(",") if project_ids else None
    
    report_data = await report_service.generate_task_completion_report(
        org_id=org_id,
        start_date=start_date,
        end_date=end_date,
        project_ids=project_list
    )
    
    if export_format == "csv":
        return _export_projects_to_csv(report_data)
    
    return report_data


@router.get("/delays-bottlenecks")
async def get_delays_bottlenecks_report(
    request: Request,
    org_id: str,
    project_ids: Optional[str] = None,
    export_format: Optional[str] = Query(None, regex="^(csv)$")
):
    """Generate delays and bottlenecks report"""
    user = await require_auth(request)
    
    membership = await get_user_org_membership(user["user_id"], org_id)
    if not membership:
        raise HTTPException(status_code=403, detail="Access denied")
    
    if not has_permission(membership["role"], Permission.REPORT_VIEW):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    project_list = project_ids.split(",") if project_ids else None
    
    report_data = await report_service.generate_delays_bottlenecks_report(
        org_id=org_id,
        project_ids=project_list
    )
    
    if export_format == "csv":
        return _export_delays_to_csv(report_data)
    
    return report_data


@router.get("/team-productivity")
async def get_team_productivity_report(
    request: Request,
    org_id: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    project_ids: Optional[str] = None,
    export_format: Optional[str] = Query(None, regex="^(csv)$")
):
    """Generate team productivity report"""
    user = await require_auth(request)
    
    membership = await get_user_org_membership(user["user_id"], org_id)
    if not membership:
        raise HTTPException(status_code=403, detail="Access denied")
    
    if not has_permission(membership["role"], Permission.REPORT_VIEW):
        raise HTTPException(status_code=403, detail="Permission denied")
    
    project_list = project_ids.split(",") if project_ids else None
    
    report_data = await report_service.generate_team_productivity_report(
        org_id=org_id,
        start_date=start_date,
        end_date=end_date,
        project_ids=project_list
    )
    
    if export_format == "csv":
        return _export_to_csv(report_data, "team_productivity")
    
    return report_data


def _export_delays_to_csv(report_data: dict) -> StreamingResponse:
    """Export delays and bottlenecks report to CSV"""
    output = io.StringIO()
    writer = csv.writer(output)
    
    writer.writerow(["Task", "Project", "Due Date", "Status", "Days Delayed"])
    
    for task in report_data.get("delayed_tasks", []):
        writer.writerow([
            task.get("title", ""),
            task.get("project_name", ""),
            task.get("due_date", ""),
            task.get("status", ""),
            task.get("days_delayed", 0)
        ])
    
    summary = report_data.get("summary", {})
    writer.writerow([])
    writer.writerow(["Total Delayed Tasks", summary.get("total_delayed", 0)])
    writer.writerow(["Average Delay", f"{summary.get('avg_delay_days', 0):.1f} days"])
    writer.writerow(["Bottleneck Projects", summary.get("bottleneck_count", 0)])
    
    output.seek(0)
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode('utf-8')),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=delays_bottlenecks_{datetime.now().strftime('%Y%m%d')}.csv"}
    )

    
def _export_to_csv(report_data: dict, filename: str) -> StreamingResponse:
    """Export time tracking report to CSV"""
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write headers
    grouped_data = report_data.get("grouped_data", [])
    if not grouped_data:
        writer.writerow(["No data available"])
    else:
        # Write headers based on keys
        headers = list(grouped_data[0].keys())
        writer.writerow(headers)
        
        # Write data rows
        for row in grouped_data:
            writer.writerow([row.get(h, "") for h in headers])
        
        # Write total
        writer.writerow([])
        writer.writerow(["Total Hours", report_data.get("total_hours", 0)])
    
    output.seek(0)
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode('utf-8')),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}_{datetime.now().strftime('%Y%m%d')}.csv"}
    )


def _export_budget_to_csv(report_data: dict) -> StreamingResponse:
    """Export budget report to CSV"""
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write headers
    writer.writerow(["Project Name", "Total Budget", "Spent", "Remaining", "Status", "Currency", "Spent %"])
    
    # Write budget data
    for budget in report_data.get("budgets", []):
        writer.writerow([
            budget.get("project_name", ""),
            budget.get("total_budget", 0),
            budget.get("spent_amount", 0),
            budget.get("remaining_amount", 0),
            budget.get("status", ""),
            budget.get("currency", ""),
            f"{budget.get('spent_percent', 0):.1f}%"
        ])
    
    # Write summary
    summary = report_data.get("summary", {})
    writer.writerow([])
    writer.writerow(["Summary"])
    writer.writerow(["Total Budget", summary.get("total_budget", 0)])
    writer.writerow(["Total Spent", summary.get("total_spent", 0)])
    writer.writerow(["Total Remaining", summary.get("total_remaining", 0)])
    writer.writerow(["Projects at Risk", summary.get("warning_count", 0) + summary.get("exceeded_count", 0)])
    
    output.seek(0)
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode('utf-8')),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=budget_report_{datetime.now().strftime('%Y%m%d')}.csv"}
    )


def _export_projects_to_csv(report_data: dict) -> StreamingResponse:
    """Export project progress report to CSV"""
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write headers
    writer.writerow(["Project Name", "Status", "Total Tasks", "Completed", "In Progress", "To Do", "Completion %"])
    
    # Write project data
    for project in report_data.get("projects", []):
        writer.writerow([
            project.get("name", ""),
            project.get("status", ""),
            project.get("total_tasks", 0),
            project.get("completed_tasks", 0),
            project.get("in_progress_tasks", 0),
            project.get("todo_tasks", 0),
            f"{project.get('completion_rate', 0):.1f}%"
        ])
    
    # Write summary
    summary = report_data.get("summary", {})
    writer.writerow([])
    writer.writerow(["Summary"])
    writer.writerow(["Total Projects", summary.get("total_projects", 0)])
    writer.writerow(["Average Completion", f"{summary.get('avg_completion_rate', 0):.1f}%"])
    writer.writerow(["Total Tasks", summary.get("total_tasks", 0)])
    writer.writerow(["Total Completed", summary.get("total_completed", 0)])
    
    output.seek(0)
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode('utf-8')),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=project_progress_{datetime.now().strftime('%Y%m%d')}.csv"}
    )
