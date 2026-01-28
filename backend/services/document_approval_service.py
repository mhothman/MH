"""
Document Approval Service - Core business logic for document approval workflows

Handles:
- Document workflow management (global/selective scopes)
- Approval requirement checking
- Approval request creation and management
- Approve/reject actions
- Timeout handling
- SLA pause/resume
- Email notifications
"""
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, List, Tuple

from core.database import get_database
from core.config import settings
from repositories.document_repository import (
    document_repository, document_workflow_repository, document_version_repository
)
from repositories.project_repository import project_repository
from services.notification_service import notification_service
from services.audit_service import audit_service
from services.email_service import email_service
from models.document import (
    DocApprovalType, DocApprovalStatus, DocApprovalAction, DocApproverRole, DocWorkflowScope
)

logger = logging.getLogger(__name__)


class DocumentApprovalService:
    """Service for managing document approval workflows"""
    
    # ==================== Document CRUD ====================
    
    async def create_document(
        self,
        org_id: str,
        title: str,
        created_by: str,
        document_type: str = "other",
        description: Optional[str] = None,
        project_id: Optional[str] = None,
        content: Optional[str] = None,
        file_url: Optional[str] = None,
        metadata: Optional[Dict] = None,
        tags: Optional[List[str]] = None
    ) -> Tuple[bool, Optional[Dict], str]:
        """Create a new document"""
        
        # Validate project if provided
        if project_id:
            project = await project_repository.find_by_id(project_id)
            if not project or project.get("org_id") != org_id:
                return False, None, "Invalid project"
        
        document_data = {
            "org_id": org_id,
            "project_id": project_id,
            "title": title,
            "description": description,
            "document_type": document_type,
            "content": content,
            "file_url": file_url,
            "metadata": metadata or {},
            "tags": tags or [],
            "owner_id": created_by,
            "created_by": created_by
        }
        
        document = await document_repository.create_document(document_data)
        
        await audit_service.log(
            user_id=created_by,
            org_id=org_id,
            action="create",
            resource_type="document",
            resource_id=document["document_id"],
            details={"title": title, "document_type": document_type}
        )
        
        logger.info(f"Document created: {document['document_id']} by {created_by}")
        return True, document, "Document created successfully"
    
    async def update_document(
        self,
        document_id: str,
        updates: Dict,
        updated_by: str,
        org_id: str
    ) -> Tuple[bool, Optional[Dict], str]:
        """Update a document"""
        
        document = await document_repository.find_by_id(document_id)
        if not document or document["org_id"] != org_id:
            return False, None, "Document not found or access denied"
        
        # Check if document is locked for approval
        if document.get("approval_locked"):
            return False, None, "Document is locked pending approval"
        
        # Increment version on content changes
        if "content" in updates or "file_url" in updates:
            await document_repository.increment_version(document_id)
        
        await document_repository.update(document_id, updates)
        
        await audit_service.log(
            user_id=updated_by,
            org_id=org_id,
            action="update",
            resource_type="document",
            resource_id=document_id,
            details=updates
        )
        
        updated = await document_repository.find_by_id(document_id)
        return True, updated, "Document updated successfully"
    
    async def delete_document(
        self,
        document_id: str,
        deleted_by: str,
        org_id: str
    ) -> Tuple[bool, str]:
        """Delete a document"""
        
        document = await document_repository.find_by_id(document_id)
        if not document or document["org_id"] != org_id:
            return False, "Document not found or access denied"
        
        if document.get("approval_locked"):
            return False, "Cannot delete document with pending approval"
        
        success = await document_repository.delete(document_id)
        
        if success:
            await audit_service.log(
                user_id=deleted_by,
                org_id=org_id,
                action="delete",
                resource_type="document",
                resource_id=document_id,
                details={"title": document.get("title")}
            )
        
        return success, "Document deleted successfully" if success else "Failed to delete document"
    
    # ==================== Workflow Management ====================
    
    async def create_workflow(
        self,
        org_id: str,
        name: str,
        description: Optional[str],
        scope: str,
        created_by: str,
        document_types: List[str] = None,
        project_ids: List[str] = None
    ) -> Tuple[bool, Optional[Dict], str]:
        """Create a new document workflow"""
        
        # Check for existing global workflow
        if scope == DocWorkflowScope.GLOBAL.value:
            existing_global = await document_workflow_repository.check_global_workflow_exists(org_id)
            if existing_global:
                return False, None, "An active global workflow already exists"
        
        workflow_data = {
            "org_id": org_id,
            "name": name,
            "description": description,
            "scope": scope,
            "document_types": document_types or [],
            "project_ids": project_ids or [],
            "created_by": created_by
        }
        
        workflow = await document_workflow_repository.create_workflow(workflow_data)
        
        await audit_service.log(
            user_id=created_by,
            org_id=org_id,
            action="create",
            resource_type="document_workflow",
            resource_id=workflow["workflow_id"],
            details={"name": name, "scope": scope}
        )
        
        logger.info(f"Document workflow created: {workflow['workflow_id']}")
        return True, workflow, "Workflow created successfully"
    
    async def update_workflow(
        self,
        workflow_id: str,
        updates: Dict,
        updated_by: str,
        org_id: str
    ) -> Tuple[bool, Optional[Dict], str]:
        """Update a workflow"""
        
        workflow = await document_workflow_repository.find_workflow_by_id(workflow_id)
        if not workflow or workflow["org_id"] != org_id:
            return False, None, "Workflow not found or access denied"
        
        # Check for global scope conflicts
        new_scope = updates.get("scope")
        new_active = updates.get("active", workflow.get("active", True))
        
        if new_scope == DocWorkflowScope.GLOBAL.value and new_active:
            existing_global = await document_workflow_repository.check_global_workflow_exists(
                org_id, exclude_workflow_id=workflow_id
            )
            if existing_global:
                return False, None, "An active global workflow already exists"
        
        await document_workflow_repository.update_workflow(workflow_id, updates)
        
        await audit_service.log(
            user_id=updated_by,
            org_id=org_id,
            action="update",
            resource_type="document_workflow",
            resource_id=workflow_id,
            details=updates
        )
        
        updated = await document_workflow_repository.find_workflow_by_id(workflow_id)
        return True, updated, "Workflow updated successfully"
    
    async def delete_workflow(
        self,
        workflow_id: str,
        deleted_by: str,
        org_id: str
    ) -> Tuple[bool, str]:
        """Delete a workflow"""
        
        workflow = await document_workflow_repository.find_workflow_by_id(workflow_id)
        if not workflow or workflow["org_id"] != org_id:
            return False, "Workflow not found or access denied"
        
        # Check for pending approvals
        rules = await document_workflow_repository.find_rules_by_workflow(workflow_id)
        rule_ids = [r["rule_id"] for r in rules]
        
        if rule_ids:
            db = get_database()
            pending_count = await db.document_approvals.count_documents({
                "workflow_rule_id": {"$in": rule_ids},
                "status": "pending"
            })
            
            if pending_count > 0:
                return False, f"Cannot delete workflow with {pending_count} pending approvals"
        
        success = await document_workflow_repository.delete_workflow(workflow_id)
        
        if success:
            await audit_service.log(
                user_id=deleted_by,
                org_id=org_id,
                action="delete",
                resource_type="document_workflow",
                resource_id=workflow_id,
                details={"name": workflow.get("name")}
            )
        
        return success, "Workflow deleted successfully" if success else "Failed to delete workflow"
    
    # ==================== Rule Management ====================
    
    async def create_rule(
        self,
        workflow_id: str,
        from_status: str,
        to_status: str,
        created_by: str,
        org_id: str,
        **kwargs
    ) -> Tuple[bool, Optional[Dict], str]:
        """Create a workflow rule"""
        
        workflow = await document_workflow_repository.find_workflow_by_id(workflow_id)
        if not workflow or workflow["org_id"] != org_id:
            return False, None, "Workflow not found or access denied"
        
        # Check for duplicate rule
        existing = await document_workflow_repository.find_rule_for_transition(
            workflow_id, from_status, to_status
        )
        if existing:
            return False, None, f"Rule already exists for {from_status} → {to_status}"
        
        rule_data = {
            "workflow_id": workflow_id,
            "from_status": from_status,
            "to_status": to_status,
            **kwargs
        }
        
        rule = await document_workflow_repository.create_rule(rule_data)
        
        await audit_service.log(
            user_id=created_by,
            org_id=org_id,
            action="create",
            resource_type="document_workflow_rule",
            resource_id=rule["rule_id"],
            details={"from_status": from_status, "to_status": to_status}
        )
        
        return True, rule, "Rule created successfully"
    
    async def update_rule(
        self,
        rule_id: str,
        updates: Dict,
        updated_by: str,
        org_id: str
    ) -> Tuple[bool, Optional[Dict], str]:
        """Update a workflow rule"""
        
        rule = await document_workflow_repository.find_rule_by_id(rule_id)
        if not rule:
            return False, None, "Rule not found"
        
        workflow = await document_workflow_repository.find_workflow_by_id(rule["workflow_id"])
        if not workflow or workflow["org_id"] != org_id:
            return False, None, "Access denied"
        
        await document_workflow_repository.update_rule(rule_id, updates)
        
        await audit_service.log(
            user_id=updated_by,
            org_id=org_id,
            action="update",
            resource_type="document_workflow_rule",
            resource_id=rule_id,
            details=updates
        )
        
        updated = await document_workflow_repository.find_rule_by_id(rule_id)
        return True, updated, "Rule updated successfully"
    
    async def delete_rule(
        self,
        rule_id: str,
        deleted_by: str,
        org_id: str
    ) -> Tuple[bool, str]:
        """Delete a workflow rule"""
        
        rule = await document_workflow_repository.find_rule_by_id(rule_id)
        if not rule:
            return False, "Rule not found"
        
        workflow = await document_workflow_repository.find_workflow_by_id(rule["workflow_id"])
        if not workflow or workflow["org_id"] != org_id:
            return False, "Access denied"
        
        # Check for pending approvals
        db = get_database()
        pending_count = await db.document_approvals.count_documents({
            "workflow_rule_id": rule_id,
            "status": "pending"
        })
        
        if pending_count > 0:
            return False, f"Cannot delete rule with {pending_count} pending approvals"
        
        success = await document_workflow_repository.delete_rule(rule_id)
        
        if success:
            await audit_service.log(
                user_id=deleted_by,
                org_id=org_id,
                action="delete",
                resource_type="document_workflow_rule",
                resource_id=rule_id,
                details={"from_status": rule["from_status"], "to_status": rule["to_status"]}
            )
        
        return success, "Rule deleted successfully" if success else "Failed to delete rule"
    
    # ==================== Approval Check & Request ====================
    
    async def check_approval_required(
        self,
        document_id: str,
        from_status: str,
        to_status: str
    ) -> Tuple[bool, Optional[Dict], Optional[Dict]]:
        """Check if a status transition requires approval"""
        
        document = await document_repository.find_by_id(document_id)
        if not document:
            return False, None, None
        
        org_id = document["org_id"]
        document_type = document.get("document_type")
        project_id = document.get("project_id")
        
        # Find applicable workflow
        workflow = await document_workflow_repository.find_applicable_workflow(
            org_id, document_type, project_id
        )
        
        if not workflow:
            return False, None, None
        
        # Find matching rule
        rule = await document_workflow_repository.find_rule_for_transition(
            workflow["workflow_id"], from_status, to_status
        )
        
        if not rule or not rule.get("approval_required", False):
            return False, None, workflow
        
        return True, rule, workflow
    
    async def request_approval(
        self,
        document_id: str,
        target_status: str,
        requested_by: str,
        org_id: str,
        comment: Optional[str] = None
    ) -> Tuple[bool, Optional[Dict], str]:
        """Request approval for a document status change"""
        
        document = await document_repository.find_by_id(document_id)
        if not document:
            return False, None, "Document not found"
        
        if document["org_id"] != org_id:
            return False, None, "Access denied"
        
        # Check for existing pending approval
        existing = await document_workflow_repository.find_pending_approval_for_document(document_id)
        if existing:
            return False, None, "Document already has a pending approval"
        
        current_status = document["status"]
        
        # Check if approval is required
        requires, rule, workflow = await self.check_approval_required(
            document_id, current_status, target_status
        )
        
        if not requires or not rule:
            return False, None, "No approval required for this transition"
        
        # Get required approvers
        required_approvers = await self._get_approvers_for_rule(rule, org_id)
        
        if not required_approvers:
            return False, None, f"No users with role {rule['approver_role']} found"
        
        # Calculate expiration
        expires_at = None
        if rule.get("approval_timeout_minutes"):
            expires_at = (
                datetime.now(timezone.utc) +
                timedelta(minutes=rule["approval_timeout_minutes"])
            ).isoformat()
        
        # Create approval request
        approval_data = {
            "document_id": document_id,
            "workflow_id": workflow["workflow_id"],
            "workflow_rule_id": rule["rule_id"],
            "org_id": org_id,
            "requested_by": requested_by,
            "original_status": current_status,
            "target_status": target_status,
            "status": DocApprovalStatus.PENDING.value,
            "approval_type": rule["approval_type"],
            "approver_role": rule["approver_role"],
            "required_approvers": required_approvers,
            "approved_by": [],
            "expires_at": expires_at,
            "pause_sla": rule.get("pause_sla", True)
        }
        
        approval = await document_workflow_repository.create_approval(approval_data)
        
        # Record the request action
        await document_workflow_repository.create_action({
            "approval_id": approval["approval_id"],
            "action": "requested",
            "acted_by": requested_by,
            "comment": comment
        })
        
        # Lock the document
        await document_repository.update(document_id, {
            "approval_locked": True,
            "pending_approval_id": approval["approval_id"]
        })
        
        # Send notifications
        if rule.get("notify_on_request", True):
            await self._notify_approvers(
                approval, document, requested_by, required_approvers, comment
            )
        
        await audit_service.log(
            user_id=requested_by,
            org_id=org_id,
            action="document_approval_requested",
            resource_type="document",
            resource_id=document_id,
            details={
                "approval_id": approval["approval_id"],
                "from_status": current_status,
                "to_status": target_status,
                "approvers": required_approvers
            }
        )
        
        logger.info(f"Document approval requested: {document_id} ({current_status} → {target_status})")
        return True, approval, "Approval request created"
    
    # ==================== Approval Actions ====================
    
    async def approve(
        self,
        approval_id: str,
        acted_by: str,
        org_id: str,
        comment: Optional[str] = None,
        is_force: bool = False
    ) -> Tuple[bool, str]:
        """Approve a document status change"""
        
        approval = await document_workflow_repository.find_approval_by_id(approval_id)
        if not approval:
            return False, "Approval not found"
        
        if approval["org_id"] != org_id:
            return False, "Access denied"
        
        if approval["status"] != DocApprovalStatus.PENDING.value:
            return False, f"Approval is already {approval['status']}"
        
        # Check authorization
        if not is_force and acted_by not in approval["required_approvers"]:
            return False, "You are not authorized to approve this request"
        
        if acted_by in approval.get("approved_by", []):
            return False, "You have already approved this request"
        
        action_type = DocApprovalAction.FORCE_APPROVE.value if is_force else DocApprovalAction.APPROVE.value
        
        # Record action
        await document_workflow_repository.create_action({
            "approval_id": approval_id,
            "action": action_type,
            "acted_by": acted_by,
            "comment": comment
        })
        
        # Add to approved_by list
        await document_workflow_repository.add_approver_to_approval(approval_id, acted_by)
        
        # Check if approval is complete
        approval_type = approval.get("approval_type", DocApprovalType.SINGLE.value)
        approved_by = approval.get("approved_by", []) + [acted_by]
        required_approvers = approval.get("required_approvers", [])
        
        is_complete = False
        if is_force:
            is_complete = True
        elif approval_type == DocApprovalType.SINGLE.value:
            is_complete = True
        elif approval_type == DocApprovalType.MULTI.value:
            is_complete = all(ra in approved_by for ra in required_approvers)
        
        if is_complete:
            return await self._complete_approval(approval, acted_by, org_id, comment)
        
        return True, "Approval recorded. Waiting for other approvers."
    
    async def reject(
        self,
        approval_id: str,
        acted_by: str,
        org_id: str,
        comment: Optional[str] = None,
        is_force: bool = False
    ) -> Tuple[bool, str]:
        """Reject a document status change"""
        
        approval = await document_workflow_repository.find_approval_by_id(approval_id)
        if not approval:
            return False, "Approval not found"
        
        if approval["org_id"] != org_id:
            return False, "Access denied"
        
        if approval["status"] != DocApprovalStatus.PENDING.value:
            return False, f"Approval is already {approval['status']}"
        
        if not is_force and acted_by not in approval["required_approvers"]:
            return False, "You are not authorized to reject this request"
        
        action_type = DocApprovalAction.FORCE_REJECT.value if is_force else DocApprovalAction.REJECT.value
        
        await document_workflow_repository.create_action({
            "approval_id": approval_id,
            "action": action_type,
            "acted_by": acted_by,
            "comment": comment
        })
        
        now = datetime.now(timezone.utc).isoformat()
        await document_workflow_repository.update_approval(approval_id, {
            "status": DocApprovalStatus.REJECTED.value,
            "rejected_by": acted_by,
            "resolved_at": now
        })
        
        document_id = approval["document_id"]
        await document_repository.update(document_id, {
            "approval_locked": False,
            "pending_approval_id": None
        })
        
        # Send notification
        rule = await document_workflow_repository.find_rule_by_id(approval["workflow_rule_id"])
        document = await document_repository.find_by_id(document_id)
        
        if rule and rule.get("notify_on_resolution", True) and document:
            await notification_service.create(
                user_id=approval["requested_by"],
                type="document_approval_rejected",
                title="Document Approval Rejected",
                message=f"Your request to change document '{document['title']}' to {approval['target_status']} was rejected.",
                link="/documents",
                metadata={"approval_id": approval_id, "comment": comment}
            )
            
            # Send email notification
            await self._send_document_approval_result_email(
                approval=approval,
                document=document,
                acted_by=acted_by,
                is_approved=False,
                comment=comment
            )
        
        await audit_service.log(
            user_id=acted_by,
            org_id=org_id,
            action="document_approval_rejected",
            resource_type="document",
            resource_id=document_id,
            details={"approval_id": approval_id, "is_force": is_force, "comment": comment}
        )
        
        logger.info(f"Document approval {approval_id} rejected by {acted_by}")
        return True, "Approval rejected"
    
    async def _complete_approval(
        self,
        approval: Dict,
        acted_by: str,
        org_id: str,
        comment: Optional[str] = None
    ) -> Tuple[bool, str]:
        """Complete the approval and update document status"""
        
        approval_id = approval["approval_id"]
        document_id = approval["document_id"]
        target_status = approval["target_status"]
        
        now = datetime.now(timezone.utc).isoformat()
        await document_workflow_repository.update_approval(approval_id, {
            "status": DocApprovalStatus.APPROVED.value,
            "resolved_at": now
        })
        
        await document_repository.update(document_id, {
            "status": target_status,
            "approval_locked": False,
            "pending_approval_id": None,
            "last_approved_at": now,
            "last_approved_by": acted_by
        })
        
        # Send notification
        rule = await document_workflow_repository.find_rule_by_id(approval["workflow_rule_id"])
        document = await document_repository.find_by_id(document_id)
        
        if rule and rule.get("notify_on_resolution", True) and document:
            await notification_service.create(
                user_id=approval["requested_by"],
                type="document_approval_approved",
                title="Document Approval Approved",
                message=f"Your request to change document '{document['title']}' to {target_status} was approved.",
                link="/documents",
                metadata={"approval_id": approval_id}
            )
            
            # Send email notification
            await self._send_document_approval_result_email(
                approval=approval,
                document=document,
                acted_by=acted_by,
                is_approved=True,
                comment=comment
            )
        
        await audit_service.log(
            user_id=acted_by,
            org_id=org_id,
            action="document_approval_approved",
            resource_type="document",
            resource_id=document_id,
            details={"approval_id": approval_id, "new_status": target_status}
        )
        
        logger.info(f"Document approval {approval_id} completed. Status changed to {target_status}")
        return True, "Approval completed. Document status updated."
    
    # ==================== Query Methods ====================
    
    async def get_document_approval_summary(
        self,
        document_id: str,
        user_id: str,
        org_id: str
    ) -> Dict:
        """Get approval summary for a document"""
        
        document = await document_repository.find_by_id(document_id)
        if not document or document["org_id"] != org_id:
            return {
                "has_pending_approval": False,
                "pending_approval": None,
                "requires_approval_for_status": [],
                "can_user_approve": False,
                "approval_history": [],
                "is_locked": False,
                "applicable_workflow": None
            }
        
        pending = await document_workflow_repository.find_pending_approval_for_document(document_id)
        
        # Get applicable workflow
        workflow = await document_workflow_repository.find_applicable_workflow(
            org_id,
            document.get("document_type"),
            document.get("project_id")
        )
        
        requires_approval_for = []
        if workflow:
            rules = await document_workflow_repository.find_rules_by_workflow(workflow["workflow_id"])
            current_status = document["status"]
            for rule in rules:
                if rule["from_status"] == current_status and rule["approval_required"]:
                    requires_approval_for.append(rule["to_status"])
        
        can_approve = False
        if pending and user_id in pending.get("required_approvers", []):
            can_approve = user_id not in pending.get("approved_by", [])
        
        # Get approval history
        db = get_database()
        all_approvals = await db.document_approvals.find(
            {"document_id": document_id},
            {"_id": 0}
        ).sort("created_at", -1).to_list(10)
        
        approval_history = []
        for appr in all_approvals:
            actions = await document_workflow_repository.find_actions_by_approval(appr["approval_id"])
            for action in actions:
                if action["acted_by"] != "system":
                    user = await db.users.find_one(
                        {"user_id": action["acted_by"]},
                        {"_id": 0, "name": 1}
                    )
                    action["actor_name"] = user.get("name") if user else "Unknown"
                else:
                    action["actor_name"] = "System"
            approval_history.extend(actions)
        
        return {
            "has_pending_approval": pending is not None,
            "pending_approval": pending,
            "requires_approval_for_status": requires_approval_for,
            "can_user_approve": can_approve,
            "approval_history": approval_history,
            "is_locked": document.get("approval_locked", False),
            "applicable_workflow": workflow
        }
    
    async def get_pending_approvals_for_user(
        self,
        user_id: str,
        org_id: str
    ) -> List[Dict]:
        """Get all pending document approvals for a user"""
        return await document_workflow_repository.find_pending_approvals_for_user(user_id, org_id)
    
    # ==================== Timeout Processing ====================
    
    async def process_expired_approvals(self) -> int:
        """Process expired document approvals"""
        expired = await document_workflow_repository.find_expired_approvals()
        processed = 0
        
        for approval in expired:
            rule = await document_workflow_repository.find_rule_by_id(approval["workflow_rule_id"])
            if not rule:
                continue
            
            if rule.get("auto_approve_on_timeout", False):
                await self.approve(
                    approval["approval_id"],
                    acted_by="system",
                    org_id=approval["org_id"],
                    comment="Auto-approved due to timeout",
                    is_force=True
                )
            else:
                now = datetime.now(timezone.utc).isoformat()
                await document_workflow_repository.update_approval(approval["approval_id"], {
                    "status": DocApprovalStatus.EXPIRED.value,
                    "resolved_at": now
                })
                
                await document_repository.update(approval["document_id"], {
                    "approval_locked": False,
                    "pending_approval_id": None
                })
                
                await document_workflow_repository.create_action({
                    "approval_id": approval["approval_id"],
                    "action": "expired",
                    "acted_by": "system",
                    "comment": "Approval expired due to timeout"
                })
                
                document = await document_repository.find_by_id(approval["document_id"])
                if document:
                    await notification_service.create(
                        user_id=approval["requested_by"],
                        type="document_approval_expired",
                        title="Document Approval Expired",
                        message=f"Your approval request for document '{document['title']}' has expired.",
                        link=f"/documents/{approval['document_id']}"
                    )
                
                await audit_service.log(
                    user_id="system",
                    org_id=approval["org_id"],
                    action="document_approval_expired",
                    resource_type="document",
                    resource_id=approval["document_id"],
                    details={"approval_id": approval["approval_id"]}
                )
            
            processed += 1
        
        if processed > 0:
            logger.info(f"Processed {processed} expired document approvals")
        
        return processed
    
    # ==================== Helper Methods ====================
    
    async def _get_approvers_for_rule(self, rule: Dict, org_id: str) -> List[str]:
        """Get list of user IDs who can approve based on the rule"""
        db = get_database()
        
        # Check for specific approvers first
        if rule.get("specific_approver_ids"):
            return rule["specific_approver_ids"]
        
        approver_role = rule.get("approver_role", DocApproverRole.ORG_ADMIN.value)
        
        # Map document approver roles to org membership roles
        role_mapping = {
            "org_admin": "org_admin",
            "project_manager": "project_manager",
            "document_owner": None,  # Will be resolved from document
            "legal": "org_admin",  # For now, legal maps to org_admin
            "compliance": "org_admin",
            "department_head": "project_manager"
        }
        
        membership_role = role_mapping.get(approver_role, "org_admin")
        
        if not membership_role:
            return []
        
        memberships = await db.org_memberships.find(
            {
                "org_id": org_id,
                "role": membership_role,
                "$or": [
                    {"status": {"$exists": False}},
                    {"status": "active"}
                ]
            },
            {"_id": 0, "user_id": 1}
        ).to_list(100)
        
        return [m["user_id"] for m in memberships]
    
    async def _notify_approvers(
        self,
        approval: Dict,
        document: Dict,
        requested_by: str,
        approvers: List[str],
        comment: Optional[str] = None
    ):
        """Send notifications and emails to approvers"""
        db = get_database()
        
        requester = await db.users.find_one(
            {"user_id": requested_by},
            {"_id": 0, "name": 1, "email": 1}
        )
        requester_name = requester.get("name", "A team member") if requester else "A team member"
        
        # Get project name if available
        project_name = None
        if document.get("project_id"):
            project = await project_repository.find_by_id(document["project_id"])
            project_name = project.get("name") if project else None
        
        # Document link
        document_link = f"{settings.FRONTEND_URL}/documents"
        
        for approver_id in approvers:
            if approver_id != requested_by:
                # In-app notification
                await notification_service.create(
                    user_id=approver_id,
                    type="document_approval_requested",
                    title="Document Approval Required",
                    message=f"{requester_name} requested approval to change document '{document['title']}' to {approval['target_status']}",
                    link="/documents",
                    metadata={
                        "approval_id": approval["approval_id"],
                        "document_id": document["document_id"]
                    }
                )
                
                # Email notification
                approver = await db.users.find_one(
                    {"user_id": approver_id},
                    {"_id": 0, "name": 1, "email": 1}
                )
                if approver and approver.get("email"):
                    try:
                        await email_service.send_document_approval_requested(
                            to=approver["email"],
                            approver_name=approver.get("name", "Team Member"),
                            requester_name=requester_name,
                            document_title=document["title"],
                            document_type=document.get("document_type", "document"),
                            from_status=approval["original_status"],
                            to_status=approval["target_status"],
                            document_link=document_link,
                            project_name=project_name,
                            comment=comment
                        )
                    except Exception as e:
                        logger.warning(f"Failed to send document approval email to {approver['email']}: {e}")
    
    async def _send_document_approval_result_email(
        self,
        approval: Dict,
        document: Dict,
        acted_by: str,
        is_approved: bool,
        comment: Optional[str] = None
    ):
        """Send email notification for approval result"""
        db = get_database()
        
        requester = await db.users.find_one(
            {"user_id": approval["requested_by"]},
            {"_id": 0, "name": 1, "email": 1}
        )
        if not requester or not requester.get("email"):
            return
        
        actor = await db.users.find_one(
            {"user_id": acted_by},
            {"_id": 0, "name": 1}
        )
        actor_name = actor.get("name", "An approver") if actor else "An approver"
        
        # Get project name if available
        project_name = None
        if document.get("project_id"):
            project = await project_repository.find_by_id(document["project_id"])
            project_name = project.get("name") if project else None
        
        document_link = f"{settings.FRONTEND_URL}/documents"
        
        try:
            if is_approved:
                await email_service.send_document_approval_approved(
                    to=requester["email"],
                    user_name=requester.get("name", "Team Member"),
                    approver_name=actor_name,
                    document_title=document["title"],
                    document_type=document.get("document_type", "document"),
                    new_status=approval["target_status"],
                    document_link=document_link,
                    project_name=project_name,
                    comment=comment
                )
            else:
                await email_service.send_document_approval_rejected(
                    to=requester["email"],
                    user_name=requester.get("name", "Team Member"),
                    rejector_name=actor_name,
                    document_title=document["title"],
                    document_type=document.get("document_type", "document"),
                    document_link=document_link,
                    project_name=project_name,
                    comment=comment
                )
        except Exception as e:
            logger.warning(f"Failed to send document approval result email: {e}")


# Singleton instance
document_approval_service = DocumentApprovalService()
