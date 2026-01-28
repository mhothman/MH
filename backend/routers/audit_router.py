"""Audit log router"""
from fastapi import APIRouter, HTTPException, Request, Query
from datetime import datetime, timezone
from typing import Optional, List
import logging
import csv
import io

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.security import require_auth, get_user_org_membership, require_permission, check_permission
from core.permissions import Permission, has_permission
from models.enums import UserRole, AuditAction, ResourceType
from models.feature_flag import Features
from services.audit_service import audit_service
from services.feature_service import feature_service

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/org/{org_id}")
async def get_audit_logs(
    org_id: str,
    request: Request,
    user_id: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    resource_type: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    limit: int = Query(100, le=500),
    skip: int = Query(0)
):
    """
    Get audit logs for an organization.
    
    Requires audit_logs feature to be enabled.
    """
    user = await require_auth(request)
    
    membership = await get_user_org_membership(user["user_id"], org_id)
    if not membership:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Check AUDIT_VIEW permission
    if not has_permission(membership["role"], Permission.AUDIT_VIEW):
        raise HTTPException(status_code=403, detail="Permission denied: cannot view audit logs")
    
    # Check feature flag
    if not await feature_service.is_enabled(org_id, Features.AUDIT_LOGS):
        raise HTTPException(status_code=403, detail="Audit logs feature not available on your plan")
    
    # Parse dates
    start = datetime.fromisoformat(start_date) if start_date else None
    end = datetime.fromisoformat(end_date) if end_date else None
    
    logs = await audit_service.get_logs(
        org_id=org_id,
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        start_date=start,
        end_date=end,
        limit=limit,
        skip=skip
    )
    
    total = await audit_service.get_log_count(org_id)
    
    return {
        "logs": logs,
        "total": total,
        "limit": limit,
        "skip": skip
    }

@router.get("/org/{org_id}/export")
async def export_audit_logs(
    org_id: str,
    request: Request,
    format: str = Query("json", regex="^(json|csv)$"),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None)
):
    """
    Export audit logs for compliance/backup.
    
    Requires data_export feature to be enabled.
    """
    user = await require_auth(request)
    
    membership = await get_user_org_membership(user["user_id"], org_id)
    if not membership:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Check AUDIT_EXPORT permission
    if not has_permission(membership["role"], Permission.AUDIT_EXPORT):
        raise HTTPException(status_code=403, detail="Permission denied: cannot export audit logs")
    
    # Check feature flag
    if not await feature_service.is_enabled(org_id, Features.DATA_EXPORT):
        raise HTTPException(status_code=403, detail="Data export feature not available on your plan")
    
    start = datetime.fromisoformat(start_date) if start_date else None
    end = datetime.fromisoformat(end_date) if end_date else None
    
    logs = await audit_service.export_logs(org_id, start, end, format)
    
    if format == "csv":
        output = io.StringIO()
        if logs:
            writer = csv.DictWriter(output, fieldnames=logs[0].keys())
            writer.writeheader()
            writer.writerows(logs)
        
        from fastapi.responses import StreamingResponse
        return StreamingResponse(
            io.BytesIO(output.getvalue().encode()),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=audit_logs_{org_id}.csv"}
        )
    
    return {"logs": logs, "count": len(logs)}

@router.get("/actions")
async def get_audit_actions():
    """Get list of all audit action types"""
    return {"actions": AuditAction.all()}

@router.get("/resource-types")
async def get_resource_types():
    """Get list of all resource types"""
    return {"resource_types": ResourceType.all()}
