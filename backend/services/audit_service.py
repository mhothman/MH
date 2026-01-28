"""Audit logging service - immutable audit records"""
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, List, Any
import logging

from core.database import get_database
from models.enums import AuditAction, ResourceType

logger = logging.getLogger(__name__)

class AuditService:
    """Service for creating and querying immutable audit logs"""
    
    @staticmethod
    async def log(
        user_id: str,
        org_id: str,
        action: str,
        resource_type: str,
        resource_id: str,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> str:
        """
        Create an immutable audit log entry.
        
        Args:
            user_id: ID of the user performing the action
            org_id: Organization ID (tenant isolation)
            action: Action performed (from AuditAction)
            resource_type: Type of resource (from ResourceType)
            resource_id: ID of the affected resource
            details: Additional details about the action
            ip_address: Client IP address
            user_agent: Client user agent
            
        Returns:
            audit_id of the created record
        """
        db = get_database()
        
        audit_id = f"audit_{uuid.uuid4().hex[:12]}"
        
        audit_record = {
            "audit_id": audit_id,
            "org_id": org_id,
            "user_id": user_id,
            "action": action,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "details": details or {},
            "ip_address": ip_address,
            "user_agent": user_agent,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            # Immutability markers
            "immutable": True,
            "checksum": None  # Could add hash for integrity verification
        }
        
        await db.audit_logs.insert_one(audit_record)
        logger.info(f"Audit log created: {action} on {resource_type}/{resource_id} by {user_id}")
        
        return audit_id
    
    @staticmethod
    async def get_logs(
        org_id: str,
        user_id: Optional[str] = None,
        action: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
        skip: int = 0
    ) -> List[Dict]:
        """
        Query audit logs with filters.
        
        All queries are scoped to org_id for tenant isolation.
        """
        db = get_database()
        
        query = {"org_id": org_id}
        
        if user_id:
            query["user_id"] = user_id
        if action:
            query["action"] = action
        if resource_type:
            query["resource_type"] = resource_type
        if resource_id:
            query["resource_id"] = resource_id
        if start_date:
            query["timestamp"] = {"$gte": start_date.isoformat()}
        if end_date:
            if "timestamp" in query:
                query["timestamp"]["$lte"] = end_date.isoformat()
            else:
                query["timestamp"] = {"$lte": end_date.isoformat()}
        
        cursor = db.audit_logs.find(query, {"_id": 0}).sort("timestamp", -1).skip(skip).limit(limit)
        
        return await cursor.to_list(limit)
    
    @staticmethod
    async def get_log_count(org_id: str, filters: Optional[Dict] = None) -> int:
        """Get total count of audit logs for pagination"""
        db = get_database()
        query = {"org_id": org_id}
        if filters:
            query.update(filters)
        return await db.audit_logs.count_documents(query)
    
    @staticmethod
    async def export_logs(
        org_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        format: str = "json"
    ) -> List[Dict]:
        """
        Export audit logs for compliance/backup.
        
        Returns all matching logs without pagination for export.
        """
        db = get_database()
        
        query = {"org_id": org_id}
        if start_date:
            query["timestamp"] = {"$gte": start_date.isoformat()}
        if end_date:
            if "timestamp" in query:
                query["timestamp"]["$lte"] = end_date.isoformat()
            else:
                query["timestamp"] = {"$lte": end_date.isoformat()}
        
        cursor = db.audit_logs.find(query, {"_id": 0}).sort("timestamp", -1)
        logs = await cursor.to_list(None)
        
        # Log the export action
        await AuditService.log(
            user_id="system",
            org_id=org_id,
            action=AuditAction.EXPORT,
            resource_type="audit_logs",
            resource_id=org_id,
            details={"count": len(logs), "format": format}
        )
        
        return logs

# Singleton instance
audit_service = AuditService()
