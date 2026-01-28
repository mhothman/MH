"""
Document and Document Approval Workflow Models

Supports formal approval workflows for documents with:
- Draft → Review → Approved → Published status transitions
- Multi-tenant isolation (tenant_id + organization_id)
- Global or selective workflow scopes
- Single or multi-approval types
"""
from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


# ==================== Document Status Enum ====================

class DocumentStatus(str, Enum):
    """Standard document statuses - extensible per organization"""
    DRAFT = "draft"
    IN_REVIEW = "in_review"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    PUBLISHED = "published"
    ARCHIVED = "archived"
    REJECTED = "rejected"


class DocumentType(str, Enum):
    """Document types for categorization"""
    POLICY = "policy"
    PROCEDURE = "procedure"
    SPECIFICATION = "specification"
    CONTRACT = "contract"
    REPORT = "report"
    PROPOSAL = "proposal"
    TEMPLATE = "template"
    OTHER = "other"


# ==================== Document Workflow Enums ====================

class DocApprovalType(str, Enum):
    """Type of approval required"""
    SINGLE = "single"  # Any one approver can approve
    MULTI = "multi"    # All approvers with the role must approve
    SEQUENTIAL = "sequential"  # Approvers approve in order


class DocApprovalStatus(str, Enum):
    """Status of a document approval request"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class DocApprovalAction(str, Enum):
    """Actions that can be taken on an approval"""
    APPROVE = "approve"
    REJECT = "reject"
    FORCE_APPROVE = "force_approve"
    FORCE_REJECT = "force_reject"
    CANCEL = "cancel"
    REQUEST_CHANGES = "request_changes"


class DocApproverRole(str, Enum):
    """Roles that can be designated as document approvers"""
    ORG_ADMIN = "org_admin"
    PROJECT_MANAGER = "project_manager"
    DOCUMENT_OWNER = "document_owner"
    LEGAL = "legal"
    COMPLIANCE = "compliance"
    DEPARTMENT_HEAD = "department_head"


class DocWorkflowScope(str, Enum):
    """Scope of document workflow application"""
    GLOBAL = "global"           # Applies to ALL documents in the organization
    SELECTIVE = "selective"     # Applies to specific projects or document types


# ==================== Document Models ====================

class DocumentCreate(BaseModel):
    """Schema for creating a new document"""
    title: str = Field(..., min_length=1, max_length=500)
    description: Optional[str] = Field(None, max_length=2000)
    document_type: DocumentType = DocumentType.OTHER
    project_id: Optional[str] = None  # Optional project association
    content: Optional[str] = None
    file_url: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    tags: List[str] = []
    
    @field_validator('title')
    @classmethod
    def title_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError('Document title cannot be empty')
        return v.strip()
    
    @field_validator('tags')
    @classmethod
    def validate_tags(cls, v: List[str]) -> List[str]:
        if len(v) > 20:
            raise ValueError('Cannot have more than 20 tags')
        return [tag.strip().lower() for tag in v if tag.strip()]


class DocumentUpdate(BaseModel):
    """Schema for updating a document"""
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    description: Optional[str] = Field(None, max_length=2000)
    document_type: Optional[DocumentType] = None
    project_id: Optional[str] = None
    content: Optional[str] = None
    file_url: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None
    
    @field_validator('title')
    @classmethod
    def title_not_empty(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not v.strip():
            raise ValueError('Document title cannot be empty')
        return v.strip() if v else v


class DocumentStatusChange(BaseModel):
    """Request to change document status"""
    target_status: str
    comment: Optional[str] = None
    
    @field_validator('target_status')
    @classmethod
    def validate_status(cls, v: str) -> str:
        valid = {s.value for s in DocumentStatus}
        if v not in valid:
            raise ValueError(f'Invalid status. Must be one of: {", ".join(valid)}')
        return v


class DocumentResponse(BaseModel):
    """Response schema for a document"""
    model_config = ConfigDict(extra="ignore")
    
    document_id: str
    org_id: str
    project_id: Optional[str] = None
    project_name: Optional[str] = None
    title: str
    description: Optional[str] = None
    document_type: str
    status: str
    version: int = 1
    content: Optional[str] = None
    file_url: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    tags: List[str] = []
    attachments: List[Dict[str, Any]] = []  # File attachments
    owner_id: str
    owner_name: Optional[str] = None
    created_by: str
    created_at: datetime
    updated_at: datetime
    # Approval info
    approval_locked: bool = False
    pending_approval_id: Optional[str] = None
    last_approved_at: Optional[datetime] = None
    last_approved_by: Optional[str] = None


# ==================== Document Attachment Models ====================

class DocumentAttachmentCreate(BaseModel):
    """Schema for adding an attachment to a document"""
    filename: str = Field(..., min_length=1, max_length=255)
    file_url: str = Field(..., min_length=1)
    file_size: int = Field(..., ge=0)  # in bytes
    mime_type: str = Field(default="application/octet-stream")
    description: Optional[str] = Field(None, max_length=500)

    @field_validator('filename')
    @classmethod
    def validate_filename(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError('Filename cannot be empty')
        return v.strip()


class DocumentAttachmentResponse(BaseModel):
    """Response schema for a document attachment"""
    attachment_id: str
    document_id: str
    filename: str
    file_url: str
    file_size: int
    mime_type: str
    description: Optional[str] = None
    uploaded_by: str
    uploaded_by_name: Optional[str] = None
    uploaded_at: datetime


# ==================== Document Version History Models ====================

class DocumentVersionResponse(BaseModel):
    """Response schema for a document version"""
    version_id: str
    document_id: str
    version_number: int
    title: str
    description: Optional[str] = None
    content: Optional[str] = None
    status: str
    changed_by: str
    changed_by_name: Optional[str] = None
    change_summary: Optional[str] = None
    created_at: datetime


class DocumentVersionCreate(BaseModel):
    """Internal model for creating a version snapshot"""
    document_id: str
    version_number: int
    title: str
    description: Optional[str] = None
    content: Optional[str] = None
    status: str
    changed_by: str
    change_summary: Optional[str] = None


# ==================== Document Workflow Models ====================

class DocumentWorkflowCreate(BaseModel):
    """Schema for creating a document workflow"""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    scope: DocWorkflowScope = DocWorkflowScope.SELECTIVE
    active: bool = True
    # Selective scope filters
    document_types: List[str] = []  # Filter by document types
    project_ids: List[str] = []      # Filter by projects
    
    @field_validator('name')
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError('Workflow name cannot be empty')
        return v.strip()


class DocumentWorkflowUpdate(BaseModel):
    """Schema for updating a document workflow"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    scope: Optional[DocWorkflowScope] = None
    active: Optional[bool] = None
    document_types: Optional[List[str]] = None
    project_ids: Optional[List[str]] = None


class DocumentWorkflowResponse(BaseModel):
    """Response schema for a document workflow"""
    model_config = ConfigDict(extra="ignore")
    
    workflow_id: str
    org_id: str
    name: str
    description: Optional[str] = None
    scope: str
    active: bool
    document_types: List[str] = []
    project_ids: List[str] = []
    rules_count: int = 0
    created_by: str
    created_at: datetime
    updated_at: datetime


class DocumentWorkflowWithRulesResponse(DocumentWorkflowResponse):
    """Response schema with rules included"""
    rules: List["DocumentWorkflowRuleResponse"] = []


# ==================== Document Workflow Rule Models ====================

class DocumentWorkflowRuleCreate(BaseModel):
    """Schema for creating a workflow rule"""
    from_status: str
    to_status: str
    description: Optional[str] = Field(None, max_length=200)
    approval_required: bool = True
    approval_type: DocApprovalType = DocApprovalType.SINGLE
    approver_role: DocApproverRole = DocApproverRole.ORG_ADMIN
    specific_approver_ids: List[str] = []  # Specific users who can approve
    approval_timeout_minutes: Optional[int] = None
    auto_approve_on_timeout: bool = False
    notify_on_request: bool = True
    notify_on_resolution: bool = True
    pause_sla: bool = True  # Pause SLA while approval is pending
    
    @field_validator('from_status', 'to_status')
    @classmethod
    def validate_status(cls, v: str) -> str:
        valid = {s.value for s in DocumentStatus}
        if v not in valid:
            raise ValueError(f'Invalid status. Must be one of: {", ".join(valid)}')
        return v


class DocumentWorkflowRuleUpdate(BaseModel):
    """Schema for updating a workflow rule"""
    from_status: Optional[str] = None
    to_status: Optional[str] = None
    description: Optional[str] = Field(None, max_length=200)
    approval_required: Optional[bool] = None
    approval_type: Optional[DocApprovalType] = None
    approver_role: Optional[DocApproverRole] = None
    specific_approver_ids: Optional[List[str]] = None
    approval_timeout_minutes: Optional[int] = None
    auto_approve_on_timeout: Optional[bool] = None
    notify_on_request: Optional[bool] = None
    notify_on_resolution: Optional[bool] = None
    pause_sla: Optional[bool] = None


class DocumentWorkflowRuleResponse(BaseModel):
    """Response schema for a workflow rule"""
    model_config = ConfigDict(extra="ignore")
    
    rule_id: str
    workflow_id: str
    from_status: str
    to_status: str
    description: Optional[str] = None
    approval_required: bool
    approval_type: str
    approver_role: str
    specific_approver_ids: List[str] = []
    approval_timeout_minutes: Optional[int] = None
    auto_approve_on_timeout: bool = False
    notify_on_request: bool = True
    notify_on_resolution: bool = True
    pause_sla: bool = True
    created_at: datetime
    updated_at: datetime


# ==================== Document Approval Models ====================

class DocumentApprovalResponse(BaseModel):
    """Response schema for a document approval"""
    model_config = ConfigDict(extra="ignore")
    
    approval_id: str
    document_id: str
    workflow_id: str
    workflow_rule_id: str
    workflow_name: Optional[str] = None
    org_id: str
    requested_by: str
    requester_name: Optional[str] = None
    original_status: str
    target_status: str
    status: str
    approval_type: str
    approver_role: str
    required_approvers: List[str] = []
    approved_by: List[str] = []
    rejected_by: Optional[str] = None
    expires_at: Optional[datetime] = None
    sla_paused_at: Optional[datetime] = None
    created_at: datetime
    resolved_at: Optional[datetime] = None


class DocumentApprovalListResponse(BaseModel):
    """Response schema for listing approvals"""
    model_config = ConfigDict(extra="ignore")
    
    approval_id: str
    document_id: str
    document_title: str
    project_id: Optional[str] = None
    project_name: Optional[str] = None
    requested_by: str
    requester_name: str
    original_status: str
    target_status: str
    status: str
    approval_type: str
    approver_role: str
    required_count: int = 0
    approved_count: int = 0
    expires_at: Optional[datetime] = None
    created_at: datetime


class DocumentApprovalActionCreate(BaseModel):
    """Schema for creating an approval action"""
    action: DocApprovalAction
    comment: Optional[str] = Field(None, max_length=1000)


class DocumentApprovalActionResponse(BaseModel):
    """Response schema for an approval action"""
    model_config = ConfigDict(extra="ignore")
    
    action_id: str
    approval_id: str
    action: str
    acted_by: str
    actor_name: Optional[str] = None
    comment: Optional[str] = None
    acted_at: datetime


# ==================== Document Approval Summary ====================

class DocumentApprovalSummary(BaseModel):
    """Summary of approval status for a document"""
    model_config = ConfigDict(extra="ignore")
    
    has_pending_approval: bool = False
    pending_approval: Optional[DocumentApprovalResponse] = None
    requires_approval_for_status: List[str] = []
    can_user_approve: bool = False
    approval_history: List[DocumentApprovalActionResponse] = []
    is_locked: bool = False
    applicable_workflow: Optional[DocumentWorkflowResponse] = None


# ==================== Request Approval Input ====================

class RequestDocApprovalInput(BaseModel):
    """Schema for requesting approval on a document status change"""
    target_status: str
    comment: Optional[str] = Field(None, max_length=1000)
    
    @field_validator('target_status')
    @classmethod
    def validate_status(cls, v: str) -> str:
        valid = {s.value for s in DocumentStatus}
        if v not in valid:
            raise ValueError(f'Invalid status. Must be one of: {", ".join(valid)}')
        return v


# Enable forward references
DocumentWorkflowWithRulesResponse.model_rebuild()
