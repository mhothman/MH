"""
Task Approval Service - Core business logic for organization-scoped approval workflows

This service handles:
- Organization-level workflow management (global/selective scopes)
- Checking if a status transition requires approval
- Creating and managing approval requests
- Processing approve/reject actions
- Handling timeouts and escalations
- Enforcing multi-tenant isolation
- Email notifications for approval events
"""
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, List, Tuple

from core.database import get_database
from core.config import settings
from repositories.workflow_repository import workflow_repository
from repositories.task_repository import task_repository
from repositories.project_repository import project_repository
from services.notification_service import notification_service
from services.audit_service import audit_service
from services.email_service import email_service
from models.workflow import (
    ApprovalType, ApprovalStatus, ApprovalAction, ApproverRole, WorkflowScope
)

logger = logging.getLogger(__name__)


class ApprovalService:
    """Service for managing organization-scoped task approval workflows"""
    
    # ==================== Workflow Management ====================
    
    async def create_workflow(
        self,
        org_id: str,
        name: str,
        description: Optional[str],
        scope: str,
        created_by: str
    ) -> Tuple[bool, Optional[Dict], str]:
        """
        Create a new workflow for an organization.
        
        Returns:
            Tuple of (success: bool, workflow: Optional[Dict], message: str)
        """
        # If creating a global workflow, check if one already exists
        if scope == WorkflowScope.GLOBAL.value:
            existing_global = await workflow_repository.check_global_workflow_exists(org_id)
            if existing_global:
                return False, None, "An active global workflow already exists. Deactivate it first or use selective scope."
        
        workflow_data = {
            "org_id": org_id,
            "name": name,
            "description": description,
            "scope": scope,
            "active": True,
            "created_by": created_by
        }
        
        workflow = await workflow_repository.create(workflow_data)
        
        # Audit log
        await audit_service.log(
            user_id=created_by,
            org_id=org_id,
            action="create",
            resource_type="workflow",
            resource_id=workflow["workflow_id"],
            details={"name": name, "scope": scope}
        )
        
        logger.info(f"Workflow created: {workflow['workflow_id']} for org {org_id} with scope {scope}")
        return True, workflow, "Workflow created successfully"
    
    async def update_workflow(
        self,
        workflow_id: str,
        updates: Dict,
        updated_by: str,
        org_id: str
    ) -> Tuple[bool, Optional[Dict], str]:
        """Update a workflow"""
        workflow = await workflow_repository.find_by_id(workflow_id)
        if not workflow or workflow["org_id"] != org_id:
            return False, None, "Workflow not found or access denied"
        
        # If changing to global scope, check for conflicts
        new_scope = updates.get("scope")
        new_active = updates.get("active", workflow.get("active", True))
        
        if new_scope == WorkflowScope.GLOBAL.value and new_active:
            existing_global = await workflow_repository.check_global_workflow_exists(
                org_id, exclude_workflow_id=workflow_id
            )
            if existing_global:
                return False, None, "An active global workflow already exists"
        
        await workflow_repository.update(workflow_id, updates)
        
        # Audit log
        await audit_service.log(
            user_id=updated_by,
            org_id=org_id,
            action="update",
            resource_type="workflow",
            resource_id=workflow_id,
            details=updates
        )
        
        updated = await workflow_repository.find_by_id(workflow_id)
        return True, updated, "Workflow updated successfully"
    
    async def delete_workflow(
        self,
        workflow_id: str,
        deleted_by: str,
        org_id: str
    ) -> Tuple[bool, str]:
        """Delete a workflow and all its rules"""
        workflow = await workflow_repository.find_by_id(workflow_id)
        if not workflow or workflow["org_id"] != org_id:
            return False, "Workflow not found or access denied"
        
        # Check for pending approvals using this workflow's rules
        rules = await workflow_repository.find_rules_by_workflow(workflow_id)
        rule_ids = [r["rule_id"] for r in rules]
        
        if rule_ids:
            db = get_database()
            pending_count = await db.task_approvals.count_documents({
                "workflow_rule_id": {"$in": rule_ids},
                "status": "pending"
            })
            
            if pending_count > 0:
                return False, f"Cannot delete workflow with {pending_count} pending approvals"
        
        success = await workflow_repository.delete(workflow_id)
        
        if success:
            await audit_service.log(
                user_id=deleted_by,
                org_id=org_id,
                action="delete",
                resource_type="workflow",
                resource_id=workflow_id,
                details={"name": workflow.get("name")}
            )
        
        return success, "Workflow deleted successfully" if success else "Failed to delete workflow"
    
    # ==================== Project Assignment ====================
    
    async def assign_projects_to_workflow(
        self,
        workflow_id: str,
        project_ids: List[str],
        assigned_by: str,
        org_id: str
    ) -> Tuple[bool, str]:
        """Assign projects to a selective workflow"""
        workflow = await workflow_repository.find_by_id(workflow_id)
        if not workflow or workflow["org_id"] != org_id:
            return False, "Workflow not found or access denied"
        
        if workflow.get("scope") != WorkflowScope.SELECTIVE.value:
            return False, "Can only assign projects to selective workflows"
        
        # Verify all projects belong to the same org
        for project_id in project_ids:
            project = await project_repository.find_by_id(project_id)
            if not project or project.get("org_id") != org_id:
                return False, f"Project {project_id} not found or doesn't belong to this organization"
        
        await workflow_repository.set_assigned_projects(workflow_id, project_ids, assigned_by)
        
        # Audit log
        await audit_service.log(
            user_id=assigned_by,
            org_id=org_id,
            action="workflow_projects_assigned",
            resource_type="workflow",
            resource_id=workflow_id,
            details={"project_ids": project_ids}
        )
        
        return True, f"Assigned {len(project_ids)} project(s) to workflow"
    
    async def get_project_applicable_workflows(
        self,
        project_id: str,
        org_id: str
    ) -> Dict:
        """Get workflows that apply to a project (read-only view)"""
        project = await project_repository.find_by_id(project_id)
        if not project:
            return {
                "project_id": project_id,
                "project_name": "Unknown",
                "global_workflow": None,
                "selective_workflows": [],
                "effective_workflow": None
            }
        
        # Get global workflow
        global_wf = await workflow_repository.find_global_workflow_for_org(org_id)
        if global_wf:
            global_wf["rules_count"] = await workflow_repository.count_rules_by_workflow(global_wf["workflow_id"])
        
        # Get selective workflows assigned to this project
        selective_wfs = await workflow_repository.find_selective_workflows_for_project(project_id)
        for wf in selective_wfs:
            wf["rules_count"] = await workflow_repository.count_rules_by_workflow(wf["workflow_id"])
        
        # Determine effective workflow (global takes priority)
        effective = global_wf if global_wf else (selective_wfs[0] if selective_wfs else None)
        
        return {
            "project_id": project_id,
            "project_name": project.get("name", "Unknown"),
            "global_workflow": global_wf,
            "selective_workflows": selective_wfs,
            "effective_workflow": effective
        }
    
    # ==================== Rule Management ====================
    
    async def create_rule(
        self,
        workflow_id: str,
        from_status: str,
        to_status: str,
        approval_required: bool,
        approval_type: str,
        approver_role: str,
        approval_timeout_minutes: Optional[int],
        auto_approve_on_timeout: bool,
        created_by: str,
        org_id: str,
        notify_on_request: bool = True,
        notify_on_resolution: bool = True,
        description: Optional[str] = None
    ) -> Tuple[bool, Optional[Dict], str]:
        """Create a workflow rule"""
        workflow = await workflow_repository.find_by_id(workflow_id)
        if not workflow or workflow["org_id"] != org_id:
            return False, None, "Workflow not found or access denied"
        
        # Check for duplicate rule
        existing = await workflow_repository.find_rule_for_transition(
            workflow_id, from_status, to_status
        )
        if existing:
            return False, None, f"Rule already exists for {from_status} -> {to_status}"
        
        rule_data = {
            "workflow_id": workflow_id,
            "from_status": from_status,
            "to_status": to_status,
            "description": description,
            "approval_required": approval_required,
            "approval_type": approval_type,
            "approver_role": approver_role,
            "approval_timeout_minutes": approval_timeout_minutes,
            "auto_approve_on_timeout": auto_approve_on_timeout,
            "notify_on_request": notify_on_request,
            "notify_on_resolution": notify_on_resolution
        }
        
        rule = await workflow_repository.create_rule(rule_data)
        
        await audit_service.log(
            user_id=created_by,
            org_id=org_id,
            action="create",
            resource_type="workflow_rule",
            resource_id=rule["rule_id"],
            details={"workflow_id": workflow_id, "from_status": from_status, "to_status": to_status}
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
        rule = await workflow_repository.find_rule_by_id(rule_id)
        if not rule:
            return False, None, "Rule not found"
        
        workflow = await workflow_repository.find_by_id(rule["workflow_id"])
        if not workflow or workflow["org_id"] != org_id:
            return False, None, "Access denied"
        
        await workflow_repository.update_rule(rule_id, updates)
        
        await audit_service.log(
            user_id=updated_by,
            org_id=org_id,
            action="update",
            resource_type="workflow_rule",
            resource_id=rule_id,
            details=updates
        )
        
        updated = await workflow_repository.find_rule_by_id(rule_id)
        return True, updated, "Rule updated successfully"
    
    async def delete_rule(
        self,
        rule_id: str,
        deleted_by: str,
        org_id: str
    ) -> Tuple[bool, str]:
        """Delete a workflow rule"""
        rule = await workflow_repository.find_rule_by_id(rule_id)
        if not rule:
            return False, "Rule not found"
        
        workflow = await workflow_repository.find_by_id(rule["workflow_id"])
        if not workflow or workflow["org_id"] != org_id:
            return False, "Access denied"
        
        # Check for pending approvals using this rule
        db = get_database()
        pending_count = await db.task_approvals.count_documents({
            "workflow_rule_id": rule_id,
            "status": "pending"
        })
        
        if pending_count > 0:
            return False, f"Cannot delete rule with {pending_count} pending approvals"
        
        success = await workflow_repository.delete_rule(rule_id)
        
        if success:
            await audit_service.log(
                user_id=deleted_by,
                org_id=org_id,
                action="delete",
                resource_type="workflow_rule",
                resource_id=rule_id,
                details={"from_status": rule["from_status"], "to_status": rule["to_status"]}
            )
        
        return success, "Rule deleted successfully" if success else "Failed to delete rule"
    
    # ==================== Approval Check & Request ====================
    
    async def check_approval_required(
        self,
        task_id: str,
        from_status: str,
        to_status: str
    ) -> Tuple[bool, Optional[Dict], Optional[Dict]]:
        """
        Check if a status transition requires approval.
        Uses organization-level workflow resolution:
        1. Check for active global workflow
        2. Fall back to selective workflows assigned to the project
        
        Returns:
            Tuple of (requires_approval: bool, rule: Optional[Dict], workflow: Optional[Dict])
        """
        task = await task_repository.find_by_id(task_id)
        if not task:
            return False, None, None
        
        project_id = task["project_id"]
        org_id = task["org_id"]
        
        # Find applicable workflow using the new resolution logic
        workflow = await workflow_repository.find_applicable_workflow_for_project(project_id, org_id)
        if not workflow:
            return False, None, None
        
        # Find matching rule
        rule = await workflow_repository.find_rule_for_transition(
            workflow["workflow_id"], from_status, to_status
        )
        
        if not rule or not rule.get("approval_required", False):
            return False, None, workflow
        
        return True, rule, workflow
    
    async def request_approval(
        self,
        task_id: str,
        target_status: str,
        requested_by: str,
        org_id: str,
        comment: Optional[str] = None
    ) -> Tuple[bool, Optional[Dict], str]:
        """
        Request approval for a task status change.
        
        Returns:
            Tuple of (success: bool, approval: Optional[Dict], message: str)
        """
        task = await task_repository.find_by_id(task_id)
        if not task:
            return False, None, "Task not found"
        
        if task["org_id"] != org_id:
            return False, None, "Access denied"
        
        # Check if there's already a pending approval
        existing = await workflow_repository.find_pending_approval_for_task(task_id)
        if existing:
            return False, None, "Task already has a pending approval"
        
        current_status = task["status"]
        
        # Check if approval is required
        requires, rule, workflow = await self.check_approval_required(task_id, current_status, target_status)
        if not requires or not rule:
            return False, None, "No approval required for this transition"
        
        # Get project for context
        project = await project_repository.find_by_id(task["project_id"])
        if not project:
            return False, None, "Project not found"
        
        # Determine required approvers
        required_approvers = await self._get_approvers_for_rule(
            rule, org_id, task["project_id"]
        )
        
        if not required_approvers:
            return False, None, f"No users with role {rule['approver_role']} found"
        
        # Calculate expiration time
        expires_at = None
        if rule.get("approval_timeout_minutes"):
            expires_at = (
                datetime.now(timezone.utc) + 
                timedelta(minutes=rule["approval_timeout_minutes"])
            ).isoformat()
        
        # Create approval request
        approval_data = {
            "org_id": org_id,
            "task_id": task_id,
            "project_id": task["project_id"],
            "workflow_id": workflow["workflow_id"],
            "workflow_rule_id": rule["rule_id"],
            "requested_by": requested_by,
            "original_status": current_status,
            "target_status": target_status,
            "status": ApprovalStatus.PENDING.value,
            "approval_type": rule["approval_type"],
            "approver_role": rule["approver_role"],
            "required_approvers": required_approvers,
            "approved_by": [],
            "rejected_by": None,
            "expires_at": expires_at
        }
        
        approval = await workflow_repository.create_approval(approval_data)
        
        # Record the request action
        await workflow_repository.create_action({
            "approval_id": approval["approval_id"],
            "action": "requested",
            "acted_by": requested_by,
            "comment": comment
        })
        
        # Lock the task
        await task_repository.update(task_id, {
            "approval_locked": True,
            "pending_approval_id": approval["approval_id"]
        })
        
        # Notify approvers if configured
        if rule.get("notify_on_request", True):
            await self._notify_approvers(
                approval, task, project, requested_by, required_approvers, comment
            )
        
        # Audit log
        await audit_service.log(
            user_id=requested_by,
            org_id=org_id,
            action="approval_requested",
            resource_type="task",
            resource_id=task_id,
            details={
                "approval_id": approval["approval_id"],
                "workflow_id": workflow["workflow_id"],
                "from_status": current_status,
                "to_status": target_status,
                "approvers": required_approvers
            }
        )
        
        logger.info(f"Approval requested for task {task_id}: {current_status} -> {target_status}")
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
        """Approve a task status change."""
        approval = await workflow_repository.find_approval_by_id(approval_id)
        if not approval:
            return False, "Approval not found"
        
        if approval["org_id"] != org_id:
            return False, "Access denied"
        
        if approval["status"] != ApprovalStatus.PENDING.value:
            return False, f"Approval is already {approval['status']}"
        
        # For non-force approvals, check if user is an authorized approver
        if not is_force and acted_by not in approval["required_approvers"]:
            return False, "You are not authorized to approve this request"
        
        # Check if already approved by this user (for multi-approval)
        if acted_by in approval.get("approved_by", []):
            return False, "You have already approved this request"
        
        action_type = ApprovalAction.FORCE_APPROVE.value if is_force else ApprovalAction.APPROVE.value
        
        # Record the action
        await workflow_repository.create_action({
            "approval_id": approval_id,
            "action": action_type,
            "acted_by": acted_by,
            "comment": comment
        })
        
        # Add to approved_by list
        await workflow_repository.add_approver_to_approval(approval_id, acted_by)
        
        # Check if approval is complete
        approval_type = approval.get("approval_type", ApprovalType.SINGLE.value)
        approved_by = approval.get("approved_by", []) + [acted_by]
        required_approvers = approval.get("required_approvers", [])
        
        is_complete = False
        if is_force:
            is_complete = True
        elif approval_type == ApprovalType.SINGLE.value:
            is_complete = True
        elif approval_type == ApprovalType.MULTI.value:
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
        """Reject a task status change."""
        approval = await workflow_repository.find_approval_by_id(approval_id)
        if not approval:
            return False, "Approval not found"
        
        if approval["org_id"] != org_id:
            return False, "Access denied"
        
        if approval["status"] != ApprovalStatus.PENDING.value:
            return False, f"Approval is already {approval['status']}"
        
        if not is_force and acted_by not in approval["required_approvers"]:
            return False, "You are not authorized to reject this request"
        
        action_type = ApprovalAction.FORCE_REJECT.value if is_force else ApprovalAction.REJECT.value
        
        await workflow_repository.create_action({
            "approval_id": approval_id,
            "action": action_type,
            "acted_by": acted_by,
            "comment": comment
        })
        
        now = datetime.now(timezone.utc).isoformat()
        await workflow_repository.update_approval(approval_id, {
            "status": ApprovalStatus.REJECTED.value,
            "rejected_by": acted_by,
            "resolved_at": now
        })
        
        task_id = approval["task_id"]
        await task_repository.update(task_id, {
            "approval_locked": False,
            "pending_approval_id": None
        })
        
        rule = await workflow_repository.find_rule_by_id(approval["workflow_rule_id"])
        task = await task_repository.find_by_id(task_id)
        project = await project_repository.find_by_id(approval["project_id"])
        
        if rule and rule.get("notify_on_resolution", True):
            # In-app notification
            await notification_service.create(
                user_id=approval["requested_by"],
                type="approval_rejected",
                title="Approval Rejected",
                message=f"Your request to change task '{task['title']}' to {approval['target_status']} was rejected.",
                link=f"/projects/{approval['project_id']}?task={task_id}",
                metadata={"approval_id": approval_id, "comment": comment}
            )
            
            # Email notification
            if task and project:
                await self._send_approval_result_email(
                    approval, task, project, acted_by, "rejected", comment
                )
        
        await audit_service.log(
            user_id=acted_by,
            org_id=org_id,
            action="approval_rejected",
            resource_type="task",
            resource_id=task_id,
            details={
                "approval_id": approval_id,
                "is_force": is_force,
                "comment": comment
            }
        )
        
        logger.info(f"Approval {approval_id} rejected by {acted_by}")
        return True, "Approval rejected"
    
    async def _complete_approval(
        self,
        approval: Dict,
        acted_by: str,
        org_id: str,
        comment: Optional[str] = None
    ) -> Tuple[bool, str]:
        """Complete the approval and update task status"""
        approval_id = approval["approval_id"]
        task_id = approval["task_id"]
        target_status = approval["target_status"]
        
        now = datetime.now(timezone.utc).isoformat()
        await workflow_repository.update_approval(approval_id, {
            "status": ApprovalStatus.APPROVED.value,
            "resolved_at": now
        })
        
        await task_repository.update(task_id, {
            "status": target_status,
            "approval_locked": False,
            "pending_approval_id": None,
            "last_approved_at": now
        })
        
        rule = await workflow_repository.find_rule_by_id(approval["workflow_rule_id"])
        task = await task_repository.find_by_id(task_id)
        project = await project_repository.find_by_id(approval["project_id"])
        
        if rule and rule.get("notify_on_resolution", True):
            # In-app notification
            await notification_service.create(
                user_id=approval["requested_by"],
                type="approval_approved",
                title="Approval Approved",
                message=f"Your request to change task '{task['title']}' to {target_status} was approved.",
                link=f"/projects/{approval['project_id']}?task={task_id}",
                metadata={"approval_id": approval_id}
            )
            
            # Email notification
            if task and project:
                await self._send_approval_result_email(
                    approval, task, project, acted_by, "approved", comment
                )
        
        await audit_service.log(
            user_id=acted_by,
            org_id=org_id,
            action="approval_approved",
            resource_type="task",
            resource_id=task_id,
            details={
                "approval_id": approval_id,
                "new_status": target_status
            }
        )
        
        logger.info(f"Approval {approval_id} completed. Task {task_id} status changed to {target_status}")
        return True, "Approval completed. Task status updated."
    
    # ==================== Timeout Processing ====================
    
    async def process_expired_approvals(self) -> int:
        """Process expired approvals. Should be called periodically."""
        expired = await workflow_repository.find_expired_approvals()
        processed = 0
        
        for approval in expired:
            rule = await workflow_repository.find_rule_by_id(approval["workflow_rule_id"])
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
                await workflow_repository.update_approval(approval["approval_id"], {
                    "status": ApprovalStatus.EXPIRED.value,
                    "resolved_at": now
                })
                
                await task_repository.update(approval["task_id"], {
                    "approval_locked": False,
                    "pending_approval_id": None
                })
                
                await workflow_repository.create_action({
                    "approval_id": approval["approval_id"],
                    "action": "expired",
                    "acted_by": "system",
                    "comment": "Approval expired due to timeout"
                })
                
                task = await task_repository.find_by_id(approval["task_id"])
                if task:
                    await notification_service.create(
                        user_id=approval["requested_by"],
                        type="approval_expired",
                        title="Approval Expired",
                        message=f"Your approval request for task '{task['title']}' has expired.",
                        link=f"/projects/{approval['project_id']}?task={approval['task_id']}"
                    )
                
                await audit_service.log(
                    user_id="system",
                    org_id=approval["org_id"],
                    action="approval_expired",
                    resource_type="task",
                    resource_id=approval["task_id"],
                    details={"approval_id": approval["approval_id"]}
                )
            
            processed += 1
        
        if processed > 0:
            logger.info(f"Processed {processed} expired approvals")
        
        return processed
    
    # ==================== Query Methods ====================
    
    async def get_task_approval_summary(
        self,
        task_id: str,
        user_id: str,
        org_id: str
    ) -> Dict:
        """Get approval summary for a task"""
        task = await task_repository.find_by_id(task_id)
        if not task or task["org_id"] != org_id:
            return {
                "has_pending_approval": False,
                "pending_approval": None,
                "requires_approval_for_status": [],
                "can_user_approve": False,
                "approval_history": [],
                "is_locked": False,
                "applicable_workflow": None
            }
        
        pending = await workflow_repository.find_pending_approval_for_task(task_id)
        
        # Get applicable workflow
        workflow = await workflow_repository.find_applicable_workflow_for_project(
            task["project_id"], org_id
        )
        
        requires_approval_for = []
        if workflow:
            rules = await workflow_repository.find_rules_by_workflow(workflow["workflow_id"])
            current_status = task["status"]
            for rule in rules:
                if rule["from_status"] == current_status and rule["approval_required"]:
                    requires_approval_for.append(rule["to_status"])
        
        can_approve = False
        if pending and user_id in pending.get("required_approvers", []):
            can_approve = user_id not in pending.get("approved_by", [])
        
        db = get_database()
        all_approvals = await db.task_approvals.find(
            {"task_id": task_id},
            {"_id": 0}
        ).sort("created_at", -1).to_list(10)
        
        approval_history = []
        for appr in all_approvals:
            actions = await workflow_repository.find_actions_by_approval(appr["approval_id"])
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
            "is_locked": task.get("approval_locked", False),
            "applicable_workflow": workflow
        }
    
    async def get_pending_approvals_for_user(
        self,
        user_id: str,
        org_id: str
    ) -> List[Dict]:
        """Get all pending approvals that a user needs to act on"""
        return await workflow_repository.find_pending_approvals_for_user(user_id, org_id)
    
    # ==================== Migration ====================
    
    async def migrate_existing_workflows(self, org_id: str) -> int:
        """
        Migrate project-level workflows to org-level selective workflows.
        Returns number of workflows migrated.
        """
        db = get_database()
        
        # Find all old project-level workflows
        old_workflows = await db.task_workflows.find(
            {
                "$or": [
                    {"project_id": {"$exists": True}},
                    {"tenant_id": {"$exists": True}, "org_id": {"$exists": False}}
                ]
            },
            {"_id": 0}
        ).to_list(500)
        
        migrated = 0
        for wf in old_workflows:
            success = await workflow_repository.migrate_project_workflow_to_org(wf["workflow_id"])
            if success:
                migrated += 1
                logger.info(f"Migrated workflow {wf['workflow_id']} to org-level")
        
        return migrated
    
    # ==================== Helper Methods ====================
    
    async def _get_approvers_for_rule(
        self,
        rule: Dict,
        org_id: str,
        project_id: str
    ) -> List[str]:
        """Get list of user IDs who can approve based on the rule's approver_role"""
        db = get_database()
        approver_role = rule.get("approver_role", ApproverRole.PROJECT_MANAGER.value)
        
        memberships = await db.org_memberships.find(
            {
                "org_id": org_id,
                "role": approver_role,
                "$or": [
                    {"status": {"$exists": False}},
                    {"status": "active"}
                ]
            },
            {"_id": 0, "user_id": 1}
        ).to_list(100)
        
        user_ids = [m["user_id"] for m in memberships]
        
        if approver_role == ApproverRole.PROJECT_MANAGER.value:
            project = await project_repository.find_by_id(project_id)
            if project and project.get("owner_id"):
                if project["owner_id"] not in user_ids:
                    user_ids.append(project["owner_id"])
        
        return user_ids
    
    async def _notify_approvers(
        self,
        approval: Dict,
        task: Dict,
        project: Dict,
        requested_by: str,
        approvers: List[str],
        comment: Optional[str] = None
    ):
        """Send notifications and emails to all approvers"""
        db = get_database()
        requester = await db.users.find_one(
            {"user_id": requested_by}, 
            {"_id": 0, "name": 1, "email": 1}
        )
        requester_name = requester.get("name", "A team member") if requester else "A team member"
        
        # Build task link
        frontend_url = settings.FRONTEND_URL if hasattr(settings, 'FRONTEND_URL') else ""
        task_link = f"{frontend_url}/projects/{project['project_id']}?task={task['task_id']}"
        
        for approver_id in approvers:
            if approver_id != requested_by:
                # In-app notification
                await notification_service.create(
                    user_id=approver_id,
                    type="approval_requested",
                    title="Approval Required",
                    message=f"{requester_name} requested approval to change task '{task['title']}' to {approval['target_status']}",
                    link=f"/projects/{project['project_id']}?task={task['task_id']}",
                    metadata={
                        "approval_id": approval["approval_id"],
                        "task_id": task["task_id"],
                        "project_id": project["project_id"]
                    }
                )
                
                # Email notification
                approver = await db.users.find_one(
                    {"user_id": approver_id},
                    {"_id": 0, "name": 1, "email": 1}
                )
                if approver and approver.get("email"):
                    try:
                        await email_service.send_approval_requested(
                            to=approver["email"],
                            approver_name=approver.get("name", "Team Member"),
                            requester_name=requester_name,
                            task_title=task["title"],
                            project_name=project.get("name", "Project"),
                            from_status=approval["original_status"],
                            to_status=approval["target_status"],
                            task_link=task_link,
                            comment=comment
                        )
                    except Exception as e:
                        logger.warning(f"Failed to send approval email to {approver['email']}: {e}")
    
    async def _send_approval_result_email(
        self,
        approval: Dict,
        task: Dict,
        project: Dict,
        acted_by: str,
        action: str,
        comment: Optional[str] = None
    ):
        """Send email notification about approval result to the requester"""
        db = get_database()
        
        # Get requester info
        requester = await db.users.find_one(
            {"user_id": approval["requested_by"]},
            {"_id": 0, "name": 1, "email": 1}
        )
        if not requester or not requester.get("email"):
            return
        
        # Get actor info
        actor = await db.users.find_one(
            {"user_id": acted_by},
            {"_id": 0, "name": 1}
        )
        actor_name = actor.get("name", "An approver") if actor else "An approver"
        
        # Build task link
        frontend_url = settings.FRONTEND_URL if hasattr(settings, 'FRONTEND_URL') else ""
        task_link = f"{frontend_url}/projects/{project['project_id']}?task={task['task_id']}"
        
        try:
            if action == "approved":
                await email_service.send_approval_approved(
                    to=requester["email"],
                    user_name=requester.get("name", "Team Member"),
                    approver_name=actor_name,
                    task_title=task["title"],
                    project_name=project.get("name", "Project"),
                    new_status=approval["target_status"],
                    task_link=task_link,
                    comment=comment
                )
            elif action == "rejected":
                await email_service.send_approval_rejected(
                    to=requester["email"],
                    user_name=requester.get("name", "Team Member"),
                    rejector_name=actor_name,
                    task_title=task["title"],
                    project_name=project.get("name", "Project"),
                    task_link=task_link,
                    comment=comment
                )
        except Exception as e:
            logger.warning(f"Failed to send approval result email: {e}")


# Singleton instance
approval_service = ApprovalService()
