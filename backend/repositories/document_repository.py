"""
Document Repository - Data access layer for documents and document workflows
"""
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, List
import uuid

from core.database import get_database

logger = logging.getLogger(__name__)


class DocumentRepository:
    """Repository for document data access"""
    
    # ==================== Document CRUD ====================
    
    async def create_document(self, data: Dict) -> Dict:
        """Create a new document"""
        db = get_database()
        
        now = datetime.now(timezone.utc).isoformat()
        document = {
            "document_id": f"doc_{uuid.uuid4().hex[:12]}",
            "org_id": data["org_id"],
            "project_id": data.get("project_id"),
            "title": data["title"],
            "description": data.get("description"),
            "document_type": data.get("document_type", "other"),
            "status": data.get("status", "draft"),
            "version": 1,
            "content": data.get("content"),
            "file_url": data.get("file_url"),
            "metadata": data.get("metadata", {}),
            "tags": data.get("tags", []),
            "owner_id": data["owner_id"],
            "created_by": data["created_by"],
            "created_at": now,
            "updated_at": now,
            "approval_locked": False,
            "pending_approval_id": None,
            "last_approved_at": None,
            "last_approved_by": None
        }
        
        await db.documents.insert_one(document)
        document.pop("_id", None)
        return document
    
    async def find_by_id(self, document_id: str) -> Optional[Dict]:
        """Find a document by ID"""
        db = get_database()
        doc = await db.documents.find_one(
            {"document_id": document_id},
            {"_id": 0}
        )
        return doc
    
    async def find_by_org(
        self,
        org_id: str,
        project_id: Optional[str] = None,
        document_type: Optional[str] = None,
        status: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict]:
        """Find documents by organization with filters"""
        db = get_database()
        
        query = {"org_id": org_id}
        
        if project_id:
            query["project_id"] = project_id
        if document_type:
            query["document_type"] = document_type
        if status:
            query["status"] = status
        if search:
            query["$or"] = [
                {"title": {"$regex": search, "$options": "i"}},
                {"description": {"$regex": search, "$options": "i"}},
                {"tags": {"$in": [search.lower()]}}
            ]
        
        docs = await db.documents.find(
            query,
            {"_id": 0}
        ).sort("updated_at", -1).skip(offset).limit(limit).to_list(limit)
        
        return docs
    
    async def update(self, document_id: str, updates: Dict) -> bool:
        """Update a document"""
        db = get_database()
        
        updates["updated_at"] = datetime.now(timezone.utc).isoformat()
        
        result = await db.documents.update_one(
            {"document_id": document_id},
            {"$set": updates}
        )
        
        return result.modified_count > 0
    
    async def delete(self, document_id: str) -> bool:
        """Delete a document"""
        db = get_database()
        result = await db.documents.delete_one({"document_id": document_id})
        return result.deleted_count > 0
    
    async def increment_version(self, document_id: str) -> int:
        """Increment document version and return new version"""
        db = get_database()
        
        result = await db.documents.find_one_and_update(
            {"document_id": document_id},
            {
                "$inc": {"version": 1},
                "$set": {"updated_at": datetime.now(timezone.utc).isoformat()}
            },
            return_document=True,
            projection={"_id": 0, "version": 1}
        )
        
        return result["version"] if result else 0


class DocumentWorkflowRepository:
    """Repository for document workflow data access"""
    
    # ==================== Workflow CRUD ====================
    
    async def create_workflow(self, data: Dict) -> Dict:
        """Create a new document workflow"""
        db = get_database()
        
        now = datetime.now(timezone.utc).isoformat()
        workflow = {
            "workflow_id": f"docwf_{uuid.uuid4().hex[:12]}",
            "org_id": data["org_id"],
            "name": data["name"],
            "description": data.get("description"),
            "scope": data.get("scope", "selective"),
            "active": data.get("active", True),
            "document_types": data.get("document_types", []),
            "project_ids": data.get("project_ids", []),
            "created_by": data["created_by"],
            "created_at": now,
            "updated_at": now
        }
        
        await db.document_workflows.insert_one(workflow)
        workflow.pop("_id", None)
        return workflow
    
    async def find_workflow_by_id(self, workflow_id: str) -> Optional[Dict]:
        """Find a workflow by ID"""
        db = get_database()
        return await db.document_workflows.find_one(
            {"workflow_id": workflow_id},
            {"_id": 0}
        )
    
    async def find_workflows_by_org(
        self,
        org_id: str,
        active_only: bool = False
    ) -> List[Dict]:
        """Find workflows by organization"""
        db = get_database()
        
        query = {"org_id": org_id}
        if active_only:
            query["active"] = True
        
        return await db.document_workflows.find(
            query,
            {"_id": 0}
        ).sort("created_at", -1).to_list(100)
    
    async def update_workflow(self, workflow_id: str, updates: Dict) -> bool:
        """Update a workflow"""
        db = get_database()
        
        updates["updated_at"] = datetime.now(timezone.utc).isoformat()
        
        result = await db.document_workflows.update_one(
            {"workflow_id": workflow_id},
            {"$set": updates}
        )
        
        return result.modified_count > 0
    
    async def delete_workflow(self, workflow_id: str) -> bool:
        """Delete a workflow and its rules"""
        db = get_database()
        
        # Delete rules first
        await db.document_workflow_rules.delete_many({"workflow_id": workflow_id})
        
        # Delete workflow
        result = await db.document_workflows.delete_one({"workflow_id": workflow_id})
        return result.deleted_count > 0
    
    async def check_global_workflow_exists(
        self,
        org_id: str,
        exclude_workflow_id: Optional[str] = None
    ) -> bool:
        """Check if an active global workflow exists"""
        db = get_database()
        
        query = {
            "org_id": org_id,
            "scope": "global",
            "active": True
        }
        
        if exclude_workflow_id:
            query["workflow_id"] = {"$ne": exclude_workflow_id}
        
        count = await db.document_workflows.count_documents(query)
        return count > 0
    
    async def find_applicable_workflow(
        self,
        org_id: str,
        document_type: Optional[str] = None,
        project_id: Optional[str] = None
    ) -> Optional[Dict]:
        """Find the applicable workflow for a document"""
        db = get_database()
        
        # First check for active global workflow
        global_wf = await db.document_workflows.find_one(
            {"org_id": org_id, "scope": "global", "active": True},
            {"_id": 0}
        )
        
        if global_wf:
            return global_wf
        
        # Find selective workflows that match
        query = {
            "org_id": org_id,
            "scope": "selective",
            "active": True,
            "$or": [
                {"document_types": {"$size": 0}, "project_ids": {"$size": 0}},  # No filters = applies to all
            ]
        }
        
        # Add matching conditions
        conditions = []
        if document_type:
            conditions.append({"document_types": document_type})
        if project_id:
            conditions.append({"project_ids": project_id})
        
        if conditions:
            query["$or"].extend(conditions)
        
        return await db.document_workflows.find_one(
            query,
            {"_id": 0},
            sort=[("created_at", 1)]  # Oldest first (most established)
        )
    
    # ==================== Workflow Rule CRUD ====================
    
    async def create_rule(self, data: Dict) -> Dict:
        """Create a workflow rule"""
        db = get_database()
        
        now = datetime.now(timezone.utc).isoformat()
        rule = {
            "rule_id": f"docrl_{uuid.uuid4().hex[:12]}",
            "workflow_id": data["workflow_id"],
            "from_status": data["from_status"],
            "to_status": data["to_status"],
            "description": data.get("description"),
            "approval_required": data.get("approval_required", True),
            "approval_type": data.get("approval_type", "single"),
            "approver_role": data.get("approver_role", "org_admin"),
            "specific_approver_ids": data.get("specific_approver_ids", []),
            "approval_timeout_minutes": data.get("approval_timeout_minutes"),
            "auto_approve_on_timeout": data.get("auto_approve_on_timeout", False),
            "notify_on_request": data.get("notify_on_request", True),
            "notify_on_resolution": data.get("notify_on_resolution", True),
            "pause_sla": data.get("pause_sla", True),
            "created_at": now,
            "updated_at": now
        }
        
        await db.document_workflow_rules.insert_one(rule)
        rule.pop("_id", None)
        return rule
    
    async def find_rule_by_id(self, rule_id: str) -> Optional[Dict]:
        """Find a rule by ID"""
        db = get_database()
        return await db.document_workflow_rules.find_one(
            {"rule_id": rule_id},
            {"_id": 0}
        )
    
    async def find_rules_by_workflow(self, workflow_id: str) -> List[Dict]:
        """Find all rules for a workflow"""
        db = get_database()
        return await db.document_workflow_rules.find(
            {"workflow_id": workflow_id},
            {"_id": 0}
        ).to_list(100)
    
    async def find_rule_for_transition(
        self,
        workflow_id: str,
        from_status: str,
        to_status: str
    ) -> Optional[Dict]:
        """Find a rule for a specific status transition"""
        db = get_database()
        return await db.document_workflow_rules.find_one(
            {
                "workflow_id": workflow_id,
                "from_status": from_status,
                "to_status": to_status
            },
            {"_id": 0}
        )
    
    async def update_rule(self, rule_id: str, updates: Dict) -> bool:
        """Update a rule"""
        db = get_database()
        
        updates["updated_at"] = datetime.now(timezone.utc).isoformat()
        
        result = await db.document_workflow_rules.update_one(
            {"rule_id": rule_id},
            {"$set": updates}
        )
        
        return result.modified_count > 0
    
    async def delete_rule(self, rule_id: str) -> bool:
        """Delete a rule"""
        db = get_database()
        result = await db.document_workflow_rules.delete_one({"rule_id": rule_id})
        return result.deleted_count > 0
    
    async def count_rules_by_workflow(self, workflow_id: str) -> int:
        """Count rules in a workflow"""
        db = get_database()
        return await db.document_workflow_rules.count_documents({"workflow_id": workflow_id})
    
    # ==================== Document Approval CRUD ====================
    
    async def create_approval(self, data: Dict) -> Dict:
        """Create a document approval request"""
        db = get_database()
        
        now = datetime.now(timezone.utc).isoformat()
        approval = {
            "approval_id": f"docap_{uuid.uuid4().hex[:12]}",
            "document_id": data["document_id"],
            "workflow_id": data["workflow_id"],
            "workflow_rule_id": data["workflow_rule_id"],
            "org_id": data["org_id"],
            "requested_by": data["requested_by"],
            "original_status": data["original_status"],
            "target_status": data["target_status"],
            "status": data.get("status", "pending"),
            "approval_type": data.get("approval_type", "single"),
            "approver_role": data.get("approver_role", "org_admin"),
            "required_approvers": data.get("required_approvers", []),
            "approved_by": data.get("approved_by", []),
            "rejected_by": None,
            "expires_at": data.get("expires_at"),
            "sla_paused_at": now if data.get("pause_sla", True) else None,
            "created_at": now,
            "resolved_at": None
        }
        
        await db.document_approvals.insert_one(approval)
        approval.pop("_id", None)
        return approval
    
    async def find_approval_by_id(self, approval_id: str) -> Optional[Dict]:
        """Find an approval by ID"""
        db = get_database()
        return await db.document_approvals.find_one(
            {"approval_id": approval_id},
            {"_id": 0}
        )
    
    async def find_pending_approval_for_document(self, document_id: str) -> Optional[Dict]:
        """Find pending approval for a document"""
        db = get_database()
        return await db.document_approvals.find_one(
            {"document_id": document_id, "status": "pending"},
            {"_id": 0}
        )
    
    async def find_approvals_by_org(
        self,
        org_id: str,
        status: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict]:
        """Find approvals by organization"""
        db = get_database()
        
        query = {"org_id": org_id}
        if status:
            query["status"] = status
        
        return await db.document_approvals.find(
            query,
            {"_id": 0}
        ).sort("created_at", -1).limit(limit).to_list(limit)
    
    async def find_pending_approvals_for_user(
        self,
        user_id: str,
        org_id: str
    ) -> List[Dict]:
        """Find pending approvals that a user can act on"""
        db = get_database()
        
        return await db.document_approvals.find(
            {
                "org_id": org_id,
                "status": "pending",
                "required_approvers": user_id,
                "approved_by": {"$ne": user_id}
            },
            {"_id": 0}
        ).sort("created_at", 1).to_list(100)
    
    async def update_approval(self, approval_id: str, updates: Dict) -> bool:
        """Update an approval"""
        db = get_database()
        
        result = await db.document_approvals.update_one(
            {"approval_id": approval_id},
            {"$set": updates}
        )
        
        return result.modified_count > 0
    
    async def add_approver_to_approval(self, approval_id: str, user_id: str) -> bool:
        """Add a user to the approved_by list"""
        db = get_database()
        
        result = await db.document_approvals.update_one(
            {"approval_id": approval_id},
            {"$addToSet": {"approved_by": user_id}}
        )
        
        return result.modified_count > 0
    
    async def find_expired_approvals(self) -> List[Dict]:
        """Find approvals that have expired"""
        db = get_database()
        
        now = datetime.now(timezone.utc).isoformat()
        
        return await db.document_approvals.find(
            {
                "status": "pending",
                "expires_at": {"$ne": None, "$lt": now}
            },
            {"_id": 0}
        ).to_list(100)
    
    # ==================== Approval Action CRUD ====================
    
    async def create_action(self, data: Dict) -> Dict:
        """Create an approval action record"""
        db = get_database()
        
        action = {
            "action_id": f"docact_{uuid.uuid4().hex[:12]}",
            "approval_id": data["approval_id"],
            "action": data["action"],
            "acted_by": data["acted_by"],
            "comment": data.get("comment"),
            "acted_at": datetime.now(timezone.utc).isoformat()
        }
        
        await db.document_approval_actions.insert_one(action)
        action.pop("_id", None)
        return action
    
    async def find_actions_by_approval(self, approval_id: str) -> List[Dict]:
        """Find all actions for an approval"""
        db = get_database()
        return await db.document_approval_actions.find(
            {"approval_id": approval_id},
            {"_id": 0}
        ).sort("acted_at", 1).to_list(100)
    
    async def get_approval_with_actions(self, approval_id: str) -> Optional[Dict]:
        """Get approval with all its actions"""
        approval = await self.find_approval_by_id(approval_id)
        if not approval:
            return None
        
        actions = await self.find_actions_by_approval(approval_id)
        approval["actions"] = actions
        return approval


class DocumentAttachmentRepository:
    """Repository for document attachment data access"""
    
    async def create(self, data: Dict) -> Dict:
        """Create a new document attachment"""
        db = get_database()
        
        attachment = {
            "attachment_id": f"docatt_{uuid.uuid4().hex[:12]}",
            "document_id": data["document_id"],
            "filename": data["filename"],
            "file_url": data["file_url"],
            "file_size": data["file_size"],
            "mime_type": data.get("mime_type", "application/octet-stream"),
            "description": data.get("description"),
            "uploaded_by": data["uploaded_by"],
            "uploaded_at": datetime.now(timezone.utc).isoformat()
        }
        
        await db.document_attachments.insert_one(attachment)
        attachment.pop("_id", None)
        return attachment
    
    async def find_by_id(self, attachment_id: str) -> Optional[Dict]:
        """Find an attachment by ID"""
        db = get_database()
        return await db.document_attachments.find_one(
            {"attachment_id": attachment_id},
            {"_id": 0}
        )
    
    async def find_by_document(self, document_id: str) -> List[Dict]:
        """Find all attachments for a document"""
        db = get_database()
        return await db.document_attachments.find(
            {"document_id": document_id},
            {"_id": 0}
        ).sort("uploaded_at", -1).to_list(100)
    
    async def delete(self, attachment_id: str) -> bool:
        """Delete an attachment"""
        db = get_database()
        result = await db.document_attachments.delete_one({"attachment_id": attachment_id})
        return result.deleted_count > 0
    
    async def delete_by_document(self, document_id: str) -> int:
        """Delete all attachments for a document"""
        db = get_database()
        result = await db.document_attachments.delete_many({"document_id": document_id})
        return result.deleted_count


class DocumentVersionRepository:
    """Repository for document version history"""
    
    async def create(self, data: Dict) -> Dict:
        """Create a new version snapshot"""
        db = get_database()
        
        version = {
            "version_id": f"docver_{uuid.uuid4().hex[:12]}",
            "document_id": data["document_id"],
            "version_number": data["version_number"],
            "title": data["title"],
            "description": data.get("description"),
            "content": data.get("content"),
            "status": data["status"],
            "changed_by": data["changed_by"],
            "change_summary": data.get("change_summary"),
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        await db.document_versions.insert_one(version)
        version.pop("_id", None)
        return version
    
    async def find_by_document(self, document_id: str, limit: int = 50) -> List[Dict]:
        """Find all versions for a document"""
        db = get_database()
        return await db.document_versions.find(
            {"document_id": document_id},
            {"_id": 0}
        ).sort("version_number", -1).limit(limit).to_list(limit)
    
    async def find_by_id(self, version_id: str) -> Optional[Dict]:
        """Find a version by ID"""
        db = get_database()
        return await db.document_versions.find_one(
            {"version_id": version_id},
            {"_id": 0}
        )
    
    async def find_latest(self, document_id: str) -> Optional[Dict]:
        """Find the latest version for a document"""
        db = get_database()
        return await db.document_versions.find_one(
            {"document_id": document_id},
            {"_id": 0},
            sort=[("version_number", -1)]
        )
    
    async def delete_by_document(self, document_id: str) -> int:
        """Delete all versions for a document"""
        db = get_database()
        result = await db.document_versions.delete_many({"document_id": document_id})
        return result.deleted_count


# Singleton instances
document_repository = DocumentRepository()
document_workflow_repository = DocumentWorkflowRepository()
document_attachment_repository = DocumentAttachmentRepository()
document_version_repository = DocumentVersionRepository()
