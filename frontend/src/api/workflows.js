/**
 * Workflows API - Organization-scoped task approval workflow endpoints
 */
import { get, post, put, del } from './client';

// ==================== Organization Workflows ====================

export const getOrgWorkflows = async (orgId, activeOnly = false) => {
  return get(`/api/workflows/org/${orgId}?active_only=${activeOnly}`);
};

export const getWorkflow = async (workflowId) => {
  return get(`/api/workflows/${workflowId}`);
};

export const createWorkflow = async (orgId, data) => {
  return post(`/api/workflows/org/${orgId}`, data);
};

export const updateWorkflow = async (workflowId, data) => {
  return put(`/api/workflows/${workflowId}`, data);
};

export const deleteWorkflow = async (workflowId) => {
  return del(`/api/workflows/${workflowId}`);
};

// ==================== Project Assignments ====================

export const assignProjectsToWorkflow = async (workflowId, projectIds) => {
  return put(`/api/workflows/${workflowId}/projects`, { project_ids: projectIds });
};

export const getWorkflowProjects = async (workflowId) => {
  return get(`/api/workflows/${workflowId}/projects`);
};

export const getApplicableWorkflowsForProject = async (projectId) => {
  return get(`/api/workflows/projects/${projectId}/applicable`);
};

// ==================== Workflow Rules ====================

export const getWorkflowRules = async (workflowId) => {
  return get(`/api/workflows/${workflowId}/rules`);
};

export const createWorkflowRule = async (workflowId, data) => {
  return post(`/api/workflows/${workflowId}/rules`, data);
};

export const updateWorkflowRule = async (ruleId, data) => {
  return put(`/api/workflows/rules/${ruleId}`, data);
};

export const deleteWorkflowRule = async (ruleId) => {
  return del(`/api/workflows/rules/${ruleId}`);
};

// ==================== Approval Actions ====================

export const requestApproval = async (taskId, targetStatus, comment = null) => {
  return post(`/api/workflows/tasks/${taskId}/request-approval`, {
    target_status: targetStatus,
    comment,
  });
};

export const approveRequest = async (approvalId, comment = null, isForce = false) => {
  return post(`/api/workflows/approvals/${approvalId}/approve`, {
    action: isForce ? 'force_approve' : 'approve',
    comment,
  });
};

export const rejectRequest = async (approvalId, comment = null, isForce = false) => {
  return post(`/api/workflows/approvals/${approvalId}/reject`, {
    action: isForce ? 'force_reject' : 'reject',
    comment,
  });
};

// ==================== Approval Queries ====================

export const getTaskApprovalSummary = async (taskId) => {
  return get(`/api/workflows/tasks/${taskId}/approval-summary`);
};

export const checkApprovalRequired = async (taskId, targetStatus) => {
  return get(`/api/workflows/tasks/${taskId}/check-approval?target_status=${targetStatus}`);
};

export const getPendingApprovals = async (orgId = null) => {
  const url = orgId 
    ? `/api/workflows/pending?org_id=${orgId}` 
    : '/api/workflows/pending';
  return get(url);
};

export const getOrgApprovals = async (orgId, status = null, limit = 50) => {
  let url = `/api/workflows/org/${orgId}/approvals?limit=${limit}`;
  if (status) {
    url += `&status=${status}`;
  }
  return get(url);
};

export const getApprovalDetail = async (approvalId) => {
  return get(`/api/workflows/approvals/${approvalId}`);
};

// ==================== Migration ====================

export const migrateWorkflows = async (orgId) => {
  return post(`/api/workflows/migrate/${orgId}`);
};
