"""Task Approval Workflow models - Organization-scoped with Global/Selective support"""
from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


# ==================== Enums ====================

class ApprovalType(str, Enum):
    """Type of approval required"""
    SINGLE = "single"  # Any one approver can approve
    MULTI = "multi"    # All approvers with the role must approve


class ApprovalStatus(str, Enum):
    """Status of an approval request"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


class ApprovalAction(str, Enum):
    """Actions that can be taken on an approval"""
    APPROVE = "approve"
    REJECT = "reject"
    FORCE_APPROVE = "force_approve"  # Admin override
    FORCE_REJECT = "force_reject"    # Admin override


class ApproverRole(str, Enum):
    """Roles that can be designated as approvers"""
    ORG_ADMIN = "org_admin"
    PROJECT_MANAGER = "project_manager"
    TEAM_MEMBER = "team_member"


class WorkflowScope(str, Enum):
    """Scope of workflow application"""
    GLOBAL = "global"      # Applies to ALL projects in the organization
    SELECTIVE = "selective"  # Applies only to assigned projects


# ==================== Task Workflow ====================

class TaskWorkflowCreate(BaseModel):
    """Schema for creating a new workflow (organization-scoped)"""
    name: str
    description: Optional[str] = None
    scope: WorkflowScope = WorkflowScope.SELECTIVE
    active: bool = True


class TaskWorkflowUpdate(BaseModel):
    """Schema for updating a workflow"""
    name: Optional[str] = None
    description: Optional[str] = None
    scope: Optional[WorkflowScope] = None
    active: Optional[bool] = None


class TaskWorkflowResponse(BaseModel):
    """Response schema for a workflow"""
    model_config = ConfigDict(extra="ignore")
    
    workflow_id: str
    org_id: str
    name: str
    description: Optional[str] = None
    scope: WorkflowScope = WorkflowScope.SELECTIVE
    active: bool = True
    rules_count: int = 0
    assigned_projects_count: int = 0  # Only for selective workflows
    assigned_projects: List[str] = []  # Project IDs for selective workflows
    created_by: str
    created_at: datetime
    updated_at: datetime


class TaskWorkflowWithRulesResponse(TaskWorkflowResponse):
    """Response schema for a workflow with its rules"""
    rules: List["TaskWorkflowRuleResponse"] = []


# ==================== Task Workflow Project Assignment ====================

class WorkflowProjectAssignment(BaseModel):
    """Schema for assigning projects to a selective workflow"""
    project_ids: List[str]


class WorkflowProjectAssignmentResponse(BaseModel):
    """Response for project assignment"""
    model_config = ConfigDict(extra="ignore")
    
    assignment_id: str
    workflow_id: str
    project_id: str
    project_name: Optional[str] = None
    assigned_at: datetime
    assigned_by: str


# ==================== Task Workflow Rule ====================

class TaskWorkflowRuleCreate(BaseModel):
    """Schema for creating a workflow rule"""
    from_status: str
    to_status: str
    description: Optional[str] = None  # Rule description for documentation
    approval_required: bool = True
    approval_type: ApprovalType = ApprovalType.SINGLE
    approver_role: ApproverRole = ApproverRole.PROJECT_MANAGER
    approval_timeout_minutes: Optional[int] = None  # None = no timeout
    auto_approve_on_timeout: bool = False
    notify_on_request: bool = True
    notify_on_resolution: bool = True


class TaskWorkflowRuleUpdate(BaseModel):
    """Schema for updating a workflow rule"""
    from_status: Optional[str] = None
    to_status: Optional[str] = None
    description: Optional[str] = None
    approval_required: Optional[bool] = None
    approval_type: Optional[ApprovalType] = None
    approver_role: Optional[ApproverRole] = None
    approval_timeout_minutes: Optional[int] = None
    auto_approve_on_timeout: Optional[bool] = None
    notify_on_request: Optional[bool] = None
    notify_on_resolution: Optional[bool] = None


class TaskWorkflowRuleResponse(BaseModel):
    """Response schema for a workflow rule"""
    model_config = ConfigDict(extra="ignore")
    
    rule_id: str
    workflow_id: str
    from_status: str
    to_status: str
    description: Optional[str] = None
    approval_required: bool = True
    approval_type: ApprovalType = ApprovalType.SINGLE
    approver_role: ApproverRole = ApproverRole.PROJECT_MANAGER
    approval_timeout_minutes: Optional[int] = None
    auto_approve_on_timeout: bool = False
    notify_on_request: bool = True
    notify_on_resolution: bool = True
    created_at: datetime
    updated_at: datetime


# ==================== Task Approval ====================

class TaskApprovalCreate(BaseModel):
    """Schema for creating an approval request (internal use)"""
    task_id: str
    workflow_rule_id: str
    requested_by: str
    original_status: str
    target_status: str


class TaskApprovalResponse(BaseModel):
    """Response schema for an approval request"""
    model_config = ConfigDict(extra="ignore")
    
    approval_id: str
    task_id: str
    workflow_rule_id: str
    workflow_id: str
    workflow_name: Optional[str] = None
    requested_by: str
    original_status: str
    target_status: str
    status: ApprovalStatus = ApprovalStatus.PENDING
    required_approvers: List[str] = []  # User IDs required for multi-approval
    approved_by: List[str] = []  # User IDs who have approved (for multi)
    rejected_by: Optional[str] = None
    expires_at: Optional[datetime] = None
    created_at: datetime
    resolved_at: Optional[datetime] = None


class TaskApprovalListResponse(BaseModel):
    """Response schema for listing approvals"""
    model_config = ConfigDict(extra="ignore")
    
    approval_id: str
    task_id: str
    task_title: str
    project_id: str
    project_name: str
    requested_by: str
    requester_name: str
    original_status: str
    target_status: str
    status: ApprovalStatus
    approval_type: ApprovalType
    approver_role: ApproverRole
    required_count: int = 0
    approved_count: int = 0
    expires_at: Optional[datetime] = None
    created_at: datetime


# ==================== Task Approval Action ====================

class TaskApprovalActionCreate(BaseModel):
    """Schema for creating an approval action"""
    action: ApprovalAction
    comment: Optional[str] = None


class TaskApprovalActionResponse(BaseModel):
    """Response schema for an approval action"""
    model_config = ConfigDict(extra="ignore")
    
    action_id: str
    approval_id: str
    action: ApprovalAction
    acted_by: str
    actor_name: Optional[str] = None
    comment: Optional[str] = None
    acted_at: datetime


# ==================== Request Approval Input ====================

class RequestApprovalInput(BaseModel):
    """Schema for requesting approval on a task status change"""
    target_status: str
    comment: Optional[str] = None


# ==================== Approval Summary (for task view) ====================

class TaskApprovalSummary(BaseModel):
    """Summary of approval status for a task"""
    model_config = ConfigDict(extra="ignore")
    
    has_pending_approval: bool = False
    pending_approval: Optional[TaskApprovalResponse] = None
    requires_approval_for_status: List[str] = []  # Statuses that need approval
    can_user_approve: bool = False
    approval_history: List[TaskApprovalActionResponse] = []
    is_locked: bool = False  # True if task is locked pending approval
    applicable_workflow: Optional[TaskWorkflowResponse] = None  # Which workflow applies


# ==================== Project Applicable Workflows ====================

class ProjectApplicableWorkflows(BaseModel):
    """Workflows that apply to a specific project (read-only view)"""
    model_config = ConfigDict(extra="ignore")
    
    project_id: str
    project_name: str
    global_workflow: Optional[TaskWorkflowResponse] = None
    selective_workflows: List[TaskWorkflowResponse] = []
    effective_workflow: Optional[TaskWorkflowResponse] = None  # The one that actually applies (global takes priority)


# Enable forward references
TaskWorkflowWithRulesResponse.model_rebuild()
