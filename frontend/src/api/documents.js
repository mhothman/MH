/**
 * Documents API - Document CRUD and approval workflow endpoints
 */
import { get, post, put, del } from './client';

// ==================== Document CRUD ====================

export const getDocuments = async (orgId, filters = {}) => {
  const params = new URLSearchParams();
  params.append('org_id', orgId);
  if (filters.project_id) params.append('project_id', filters.project_id);
  if (filters.document_type) params.append('document_type', filters.document_type);
  if (filters.status) params.append('status', filters.status);
  if (filters.search) params.append('search', filters.search);
  if (filters.limit) params.append('limit', filters.limit);
  if (filters.offset) params.append('offset', filters.offset);
  
  return get(`/api/documents/?${params.toString()}`);
};

export const getDocument = async (documentId) => {
  return get(`/api/documents/${documentId}`);
};

export const createDocument = async (orgId, data) => {
  return post(`/api/documents/?org_id=${orgId}`, data);
};

export const updateDocument = async (documentId, data) => {
  return put(`/api/documents/${documentId}`, data);
};

export const deleteDocument = async (documentId) => {
  return del(`/api/documents/${documentId}`);
};

// ==================== Document Status ====================

export const changeDocumentStatus = async (documentId, targetStatus, comment = null) => {
  return post(`/api/documents/${documentId}/change-status`, {
    target_status: targetStatus,
    comment,
  });
};

export const checkDocumentApprovalRequired = async (documentId, targetStatus) => {
  return get(`/api/documents/${documentId}/check-approval?target_status=${targetStatus}`);
};

export const getDocumentApprovalSummary = async (documentId) => {
  return get(`/api/documents/${documentId}/approval-summary`);
};

// ==================== Document Types & Statuses ====================

export const getDocumentTypes = async () => {
  return get('/api/documents/types');
};

export const getDocumentStatuses = async () => {
  return get('/api/documents/statuses');
};

// ==================== Document Workflows ====================

export const getDocumentWorkflows = async (orgId, activeOnly = false) => {
  return get(`/api/documents/workflows/?org_id=${orgId}&active_only=${activeOnly}`);
};

export const getDocumentWorkflow = async (workflowId) => {
  return get(`/api/documents/workflows/${workflowId}`);
};

export const createDocumentWorkflow = async (orgId, data) => {
  return post(`/api/documents/workflows/?org_id=${orgId}`, data);
};

export const updateDocumentWorkflow = async (workflowId, data) => {
  return put(`/api/documents/workflows/${workflowId}`, data);
};

export const deleteDocumentWorkflow = async (workflowId) => {
  return del(`/api/documents/workflows/${workflowId}`);
};

// ==================== Document Workflow Rules ====================

export const getDocumentWorkflowRules = async (workflowId) => {
  return get(`/api/documents/workflows/${workflowId}/rules`);
};

export const createDocumentWorkflowRule = async (workflowId, data) => {
  return post(`/api/documents/workflows/${workflowId}/rules`, data);
};

export const updateDocumentWorkflowRule = async (ruleId, data) => {
  return put(`/api/documents/workflows/rules/${ruleId}`, data);
};

export const deleteDocumentWorkflowRule = async (ruleId) => {
  return del(`/api/documents/workflows/rules/${ruleId}`);
};

// ==================== Document Approvals ====================

export const getPendingDocumentApprovals = async (orgId = null) => {
  const url = orgId 
    ? `/api/documents/workflows/pending?org_id=${orgId}` 
    : '/api/documents/workflows/pending';
  return get(url);
};

export const getOrgDocumentApprovals = async (orgId, status = null, limit = 50) => {
  let url = `/api/documents/org/${orgId}/approvals?limit=${limit}`;
  if (status) {
    url += `&status=${status}`;
  }
  return get(url);
};

export const getDocumentApprovalDetail = async (approvalId) => {
  return get(`/api/documents/approvals/${approvalId}`);
};

// ==================== Document Attachments ====================

export const getDocumentAttachments = async (documentId) => {
  return get(`/api/documents/${documentId}/attachments`);
};

export const addDocumentAttachment = async (documentId, data) => {
  return post(`/api/documents/${documentId}/attachments`, data);
};

export const uploadDocumentFile = async (documentId, file) => {
  const formData = new FormData();
  formData.append('file', file);
  
  const API_URL = process.env.REACT_APP_BACKEND_URL;
  const token = localStorage.getItem('proflow_token');
  
  const response = await fetch(`${API_URL}/api/documents/${documentId}/upload`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
    },
    body: formData,
  });
  
  const data = await response.json();
  
  if (!response.ok) {
    throw new Error(data.detail || 'Upload failed');
  }
  
  return data;
};

export const deleteDocumentAttachment = async (attachmentId) => {
  return del(`/api/documents/attachments/${attachmentId}`);
};

// ==================== Document Version History ====================

export const getDocumentVersions = async (documentId, limit = 50) => {
  return get(`/api/documents/${documentId}/versions?limit=${limit}`);
};

export const getDocumentVersion = async (versionId) => {
  return get(`/api/documents/versions/${versionId}`);
};

export const createDocumentVersion = async (documentId, changeSummary = null) => {
  const params = changeSummary ? `?change_summary=${encodeURIComponent(changeSummary)}` : '';
  return post(`/api/documents/${documentId}/versions${params}`, {});
};

export const approveDocumentRequest = async (approvalId, comment = null, isForce = false) => {
  return post(`/api/documents/approvals/${approvalId}/approve`, {
    action: isForce ? 'force_approve' : 'approve',
    comment,
  });
};

export const rejectDocumentRequest = async (approvalId, comment = null, isForce = false) => {
  return post(`/api/documents/approvals/${approvalId}/reject`, {
    action: isForce ? 'force_reject' : 'reject',
    comment,
  });
};

// Document status constants
export const DocumentStatus = {
  DRAFT: 'draft',
  IN_REVIEW: 'in_review',
  PENDING_APPROVAL: 'pending_approval',
  APPROVED: 'approved',
  PUBLISHED: 'published',
  ARCHIVED: 'archived',
  REJECTED: 'rejected',
};

export const DocumentType = {
  POLICY: 'policy',
  PROCEDURE: 'procedure',
  SPECIFICATION: 'specification',
  CONTRACT: 'contract',
  REPORT: 'report',
  PROPOSAL: 'proposal',
  TEMPLATE: 'template',
  OTHER: 'other',
};

// Status color mapping for UI
export const getStatusColor = (status) => {
  const colors = {
    draft: '#6b7280',
    in_review: '#f59e0b',
    pending_approval: '#8b5cf6',
    approved: '#22c55e',
    published: '#3b82f6',
    archived: '#9ca3af',
    rejected: '#ef4444',
  };
  return colors[status] || '#6b7280';
};

// Status label mapping for UI
export const getStatusLabel = (status) => {
  const labels = {
    draft: 'Draft',
    in_review: 'In Review',
    pending_approval: 'Pending Approval',
    approved: 'Approved',
    published: 'Published',
    archived: 'Archived',
    rejected: 'Rejected',
  };
  return labels[status] || status;
};

// Document type label mapping for UI
export const getTypeLabel = (type) => {
  const labels = {
    policy: 'Policy',
    procedure: 'Procedure',
    specification: 'Specification',
    contract: 'Contract',
    report: 'Report',
    proposal: 'Proposal',
    template: 'Template',
    other: 'Other',
  };
  return labels[type] || type;
};
