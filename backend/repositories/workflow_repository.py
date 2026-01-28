"""Workflow Repository - Data access layer for organization-scoped task approval workflows"""
from typing import Dict, List, Optional
from datetime import datetime, timezone
import uuid

from core.database import get_database
from repositories import BaseRepository


class WorkflowRepository(BaseRepository):
    """Repository for workflow data access - Organization-scoped"""
    
    @property
    def collection_name(self) -> str:
        return "task_workflows"
    
    @property
    def id_field(self) -> str:
        return "workflow_id"
    
    # ==================== Task Workflow CRUD ====================
    
    async def find_by_id(self, workflow_id: str) -> Optional[Dict]:
        """Find workflow by ID"""
        db = get_database()
        return await db.task_workflows.find_one({self.id_field: workflow_id}, {"_id": 0})
    
    async def find_all(self, query: Dict = None, limit: int = 100) -> List[Dict]:
        """Find all workflows matching query"""
        db = get_database()
        return await db.task_workflows.find(query or {}, {"_id": 0}).to_list(limit)
    
    async def find_by_org(self, org_id: str, active_only: bool = False) -> List[Dict]:
        """Find all workflows for an organization"""
        db = get_database()
        query = {"org_id": org_id}
        if active_only:
            query["active"] = True
        return await db.task_workflows.find(query, {"_id": 0}).sort("created_at", -1).to_list(100)
    
    async def find_global_workflow_for_org(self, org_id: str) -> Optional[Dict]:
        """Find the active global workflow for an organization (only one allowed)"""
        db = get_database()
        return await db.task_workflows.find_one(
            {"org_id": org_id, "scope": "global", "active": True}, 
            {"_id": 0}
        )
    
    async def find_selective_workflows_for_project(self, project_id: str) -> List[Dict]:
        """Find active selective workflows assigned to a project"""
        db = get_database()
        # Get workflow IDs assigned to this project
        assignments = await db.task_workflow_projects.find(
            {"project_id": project_id},
            {"_id": 0, "workflow_id": 1}
        ).to_list(100)
        
        if not assignments:
            return []
        
        workflow_ids = [a["workflow_id"] for a in assignments]
        
        # Get active workflows
        workflows = await db.task_workflows.find(
            {
                "workflow_id": {"$in": workflow_ids},
                "scope": "selective",
                "active": True
            },
            {"_id": 0}
        ).to_list(100)
        
        return workflows
    
    async def find_applicable_workflow_for_project(self, project_id: str, org_id: str) -> Optional[Dict]:
        """
        Find the workflow that applies to a project.
        Priority: Global workflow > Selective workflows (first active)
        """
        # Check for global workflow first
        global_wf = await self.find_global_workflow_for_org(org_id)
        if global_wf:
            return global_wf
        
        # Fall back to selective workflows
        selective_wfs = await self.find_selective_workflows_for_project(project_id)
        if selective_wfs:
            return selective_wfs[0]  # Return first active selective workflow
        
        return None
    
    async def check_global_workflow_exists(self, org_id: str, exclude_workflow_id: str = None) -> bool:
        """Check if an active global workflow already exists for the org"""
        db = get_database()
        query = {"org_id": org_id, "scope": "global", "active": True}
        if exclude_workflow_id:
            query["workflow_id"] = {"$ne": exclude_workflow_id}
        count = await db.task_workflows.count_documents(query)
        return count > 0
    
    async def create(self, data: Dict) -> Dict:
        """Create a new workflow"""
        db = get_database()
        workflow_id = f"wf_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc).isoformat()
        
        workflow = {
            "workflow_id": workflow_id,
            **data,
            "created_at": now,
            "updated_at": now
        }
        
        await db.task_workflows.insert_one(workflow)
        workflow.pop("_id", None)
        return workflow
    
    async def update(self, workflow_id: str, data: Dict) -> bool:
        """Update a workflow"""
        db = get_database()
        data["updated_at"] = datetime.now(timezone.utc).isoformat()
        result = await db.task_workflows.update_one(
            {self.id_field: workflow_id},
            {"$set": data}
        )
        return result.modified_count > 0
    
    async def delete(self, workflow_id: str) -> bool:
        """Delete a workflow, its rules, and project assignments"""
        db = get_database()
        # Delete associated rules first
        await db.task_workflow_rules.delete_many({"workflow_id": workflow_id})
        # Delete project assignments
        await db.task_workflow_projects.delete_many({"workflow_id": workflow_id})
        # Delete the workflow
        result = await db.task_workflows.delete_one({self.id_field: workflow_id})
        return result.deleted_count > 0
    
    # ==================== Workflow Project Assignments ====================
    
    async def get_assigned_projects(self, workflow_id: str) -> List[Dict]:
        """Get all projects assigned to a workflow"""
        db = get_database()
        return await db.task_workflow_projects.find(
            {"workflow_id": workflow_id},
            {"_id": 0}
        ).to_list(500)
    
    async def assign_project(self, workflow_id: str, project_id: str, assigned_by: str) -> Dict:
        """Assign a project to a workflow"""
        db = get_database()
        
        # Check if already assigned
        existing = await db.task_workflow_projects.find_one(
            {"workflow_id": workflow_id, "project_id": project_id}
        )
        if existing:
            return {**existing, "_id": None}
        
        assignment_id = f"wfp_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc).isoformat()
        
        assignment = {
            "assignment_id": assignment_id,
            "workflow_id": workflow_id,
            "project_id": project_id,
            "assigned_by": assigned_by,
            "assigned_at": now
        }
        
        await db.task_workflow_projects.insert_one(assignment)
        assignment.pop("_id", None)
        return assignment
    
    async def unassign_project(self, workflow_id: str, project_id: str) -> bool:
        """Remove a project from a workflow"""
        db = get_database()
        result = await db.task_workflow_projects.delete_one(
            {"workflow_id": workflow_id, "project_id": project_id}
        )
        return result.deleted_count > 0
    
    async def set_assigned_projects(self, workflow_id: str, project_ids: List[str], assigned_by: str) -> List[Dict]:
        """Set the complete list of assigned projects (replaces existing)"""
        db = get_database()
        
        # Remove all existing assignments
        await db.task_workflow_projects.delete_many({"workflow_id": workflow_id})
        
        # Add new assignments
        assignments = []
        for project_id in project_ids:
            assignment = await self.assign_project(workflow_id, project_id, assigned_by)
            assignments.append(assignment)
        
        return assignments
    
    async def count_assigned_projects(self, workflow_id: str) -> int:
        """Count projects assigned to a workflow"""
        db = get_database()
        return await db.task_workflow_projects.count_documents({"workflow_id": workflow_id})
    
    async def get_workflows_for_project(self, project_id: str) -> List[str]:
        """Get workflow IDs assigned to a project"""
        db = get_database()
        assignments = await db.task_workflow_projects.find(
            {"project_id": project_id},
            {"_id": 0, "workflow_id": 1}
        ).to_list(100)
        return [a["workflow_id"] for a in assignments]
    
    # ==================== Task Workflow Rule CRUD ====================
    
    async def find_rule_by_id(self, rule_id: str) -> Optional[Dict]:
        """Find workflow rule by ID"""
        db = get_database()
        return await db.task_workflow_rules.find_one({"rule_id": rule_id}, {"_id": 0})
    
    async def find_rules_by_workflow(self, workflow_id: str) -> List[Dict]:
        """Find all rules for a workflow"""
        db = get_database()
        return await db.task_workflow_rules.find(
            {"workflow_id": workflow_id}, 
            {"_id": 0}
        ).to_list(100)
    
    async def find_rule_for_transition(
        self, 
        workflow_id: str, 
        from_status: str, 
        to_status: str
    ) -> Optional[Dict]:
        """Find a rule that matches a specific status transition"""
        db = get_database()
        return await db.task_workflow_rules.find_one(
            {
                "workflow_id": workflow_id,
                "from_status": from_status,
                "to_status": to_status
            },
            {"_id": 0}
        )
    
    async def create_rule(self, data: Dict) -> Dict:
        """Create a new workflow rule"""
        db = get_database()
        rule_id = f"wfr_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc).isoformat()
        
        rule = {
            "rule_id": rule_id,
            **data,
            "created_at": now,
            "updated_at": now
        }
        
        await db.task_workflow_rules.insert_one(rule)
        rule.pop("_id", None)
        return rule
    
    async def update_rule(self, rule_id: str, data: Dict) -> bool:
        """Update a workflow rule"""
        db = get_database()
        data["updated_at"] = datetime.now(timezone.utc).isoformat()
        result = await db.task_workflow_rules.update_one(
            {"rule_id": rule_id},
            {"$set": data}
        )
        return result.modified_count > 0
    
    async def delete_rule(self, rule_id: str) -> bool:
        """Delete a workflow rule"""
        db = get_database()
        result = await db.task_workflow_rules.delete_one({"rule_id": rule_id})
        return result.deleted_count > 0
    
    async def count_rules_by_workflow(self, workflow_id: str) -> int:
        """Count rules for a workflow"""
        db = get_database()
        return await db.task_workflow_rules.count_documents({"workflow_id": workflow_id})
    
    # ==================== Task Approval CRUD ====================
    
    async def find_approval_by_id(self, approval_id: str) -> Optional[Dict]:
        """Find approval by ID"""
        db = get_database()
        return await db.task_approvals.find_one({"approval_id": approval_id}, {"_id": 0})
    
    async def find_approval_by_task(self, task_id: str, status: str = None) -> Optional[Dict]:
        """Find approval for a task, optionally filtered by status"""
        db = get_database()
        query = {"task_id": task_id}
        if status:
            query["status"] = status
        return await db.task_approvals.find_one(query, {"_id": 0})
    
    async def find_pending_approval_for_task(self, task_id: str) -> Optional[Dict]:
        """Find pending approval for a task"""
        return await self.find_approval_by_task(task_id, "pending")
    
    async def find_approvals_by_project(
        self, 
        project_id: str, 
        status: str = None,
        limit: int = 100
    ) -> List[Dict]:
        """Find approvals for a project"""
        db = get_database()
        query = {"project_id": project_id}
        if status:
            query["status"] = status
        return await db.task_approvals.find(query, {"_id": 0}).sort("created_at", -1).to_list(limit)
    
    async def find_approvals_by_org(
        self,
        org_id: str,
        status: str = None,
        limit: int = 100
    ) -> List[Dict]:
        """Find approvals for an organization"""
        db = get_database()
        query = {"org_id": org_id}
        if status:
            query["status"] = status
        return await db.task_approvals.find(query, {"_id": 0}).sort("created_at", -1).to_list(limit)
    
    async def find_pending_approvals_for_user(
        self, 
        user_id: str, 
        org_id: str
    ) -> List[Dict]:
        """Find pending approvals where user is a required approver"""
        db = get_database()
        return await db.task_approvals.find(
            {
                "org_id": org_id,
                "status": "pending",
                "required_approvers": user_id,
                "approved_by": {"$ne": user_id}  # Not already approved by this user
            },
            {"_id": 0}
        ).sort("created_at", -1).to_list(100)
    
    async def find_expired_approvals(self) -> List[Dict]:
        """Find approvals that have expired but not yet marked as expired"""
        db = get_database()
        now = datetime.now(timezone.utc).isoformat()
        return await db.task_approvals.find(
            {
                "status": "pending",
                "expires_at": {"$lt": now, "$ne": None}
            },
            {"_id": 0}
        ).to_list(500)
    
    async def create_approval(self, data: Dict) -> Dict:
        """Create a new approval request"""
        db = get_database()
        approval_id = f"appr_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc).isoformat()
        
        approval = {
            "approval_id": approval_id,
            **data,
            "created_at": now
        }
        
        await db.task_approvals.insert_one(approval)
        approval.pop("_id", None)
        return approval
    
    async def update_approval(self, approval_id: str, data: Dict) -> bool:
        """Update an approval"""
        db = get_database()
        result = await db.task_approvals.update_one(
            {"approval_id": approval_id},
            {"$set": data}
        )
        return result.modified_count > 0
    
    async def add_approver_to_approval(self, approval_id: str, user_id: str) -> bool:
        """Add a user to the approved_by list"""
        db = get_database()
        result = await db.task_approvals.update_one(
            {"approval_id": approval_id},
            {"$addToSet": {"approved_by": user_id}}
        )
        return result.modified_count > 0
    
    # ==================== Task Approval Action CRUD ====================
    
    async def find_actions_by_approval(self, approval_id: str) -> List[Dict]:
        """Find all actions for an approval"""
        db = get_database()
        return await db.task_approval_actions.find(
            {"approval_id": approval_id},
            {"_id": 0}
        ).sort("acted_at", 1).to_list(100)
    
    async def create_action(self, data: Dict) -> Dict:
        """Create an approval action record"""
        db = get_database()
        action_id = f"act_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc).isoformat()
        
        action = {
            "action_id": action_id,
            **data,
            "acted_at": now
        }
        
        await db.task_approval_actions.insert_one(action)
        action.pop("_id", None)
        return action
    
    # ==================== Utility Methods ====================
    
    async def get_workflow_with_rules(self, workflow_id: str) -> Optional[Dict]:
        """Get a workflow with all its rules and project assignments"""
        workflow = await self.find_by_id(workflow_id)
        if not workflow:
            return None
        
        rules = await self.find_rules_by_workflow(workflow_id)
        workflow["rules"] = rules
        workflow["rules_count"] = len(rules)
        
        # Get assigned projects for selective workflows
        if workflow.get("scope") == "selective":
            assignments = await self.get_assigned_projects(workflow_id)
            workflow["assigned_projects"] = [a["project_id"] for a in assignments]
            workflow["assigned_projects_count"] = len(assignments)
        else:
            workflow["assigned_projects"] = []
            workflow["assigned_projects_count"] = 0
        
        return workflow
    
    async def get_approval_with_actions(self, approval_id: str) -> Optional[Dict]:
        """Get an approval with all its actions"""
        approval = await self.find_approval_by_id(approval_id)
        if not approval:
            return None
        
        actions = await self.find_actions_by_approval(approval_id)
        approval["actions"] = actions
        return approval
    
    # ==================== Migration Helper ====================
    
    async def migrate_project_workflow_to_org(self, workflow_id: str) -> bool:
        """
        Migrate a project-level workflow to org-level selective workflow.
        Sets scope to 'selective' and creates project assignment.
        """
        db = get_database()
        workflow = await self.find_by_id(workflow_id)
        if not workflow:
            return False
        
        project_id = workflow.get("project_id")
        org_id = workflow.get("tenant_id") or workflow.get("org_id")
        
        if not project_id or not org_id:
            return False
        
        # Update workflow to org-level
        await db.task_workflows.update_one(
            {"workflow_id": workflow_id},
            {
                "$set": {
                    "org_id": org_id,
                    "scope": "selective",
                    "updated_at": datetime.now(timezone.utc).isoformat()
                },
                "$unset": {
                    "project_id": "",
                    "tenant_id": ""
                }
            }
        )
        
        # Create project assignment
        await self.assign_project(workflow_id, project_id, "system_migration")
        
        return True


# Singleton instance
workflow_repository = WorkflowRepository()
