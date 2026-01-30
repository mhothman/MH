/**
 * Budget Approval API client functions
 */
import { get, post } from './client';

// ==================== Budget Approval Operations ====================

export const requestBudgetChange = async (orgId, approvalData) => {
  return post(`/api/budget-approvals/request?org_id=${orgId}`, approvalData);
};

export const approveBudgetChange = async (approvalId, orgId, notes = null) => {
  return post(`/api/budget-approvals/${approvalId}/approve?org_id=${orgId}`, { notes });
};

export const rejectBudgetChange = async (approvalId, orgId, notes = null) => {
  return post(`/api/budget-approvals/${approvalId}/reject?org_id=${orgId}`, { notes });
};

export const getPendingApprovals = async (orgId) => {
  return get(`/api/budget-approvals/pending/org/${orgId}`);
};

export const getApproval = async (approvalId) => {
  return get(`/api/budget-approvals/${approvalId}`);
};

export const getBudgetApprovalHistory = async (budgetId) => {
  return get(`/api/budget-approvals/budget/${budgetId}`);
};

// ==================== Constants ====================

export const BUDGET_CHANGE_TYPES = {
  amount_increase: { label: 'Budget Increase', icon: 'trending-up', color: 'text-green-500' },
  amount_decrease: { label: 'Budget Decrease', icon: 'trending-down', color: 'text-red-500' },
  threshold_change: { label: 'Threshold Change', icon: 'alert-triangle', color: 'text-yellow-500' },
  hard_limit_change: { label: 'Hard Limit Change', icon: 'lock', color: 'text-orange-500' },
  other: { label: 'Other Change', icon: 'edit', color: 'text-gray-500' },
};

export const APPROVAL_STATUS = {
  pending: { label: 'Pending', color: 'bg-yellow-500', textColor: 'text-yellow-500', variant: 'default' },
  approved: { label: 'Approved', color: 'bg-green-500', textColor: 'text-green-500', variant: 'default' },
  rejected: { label: 'Rejected', color: 'bg-red-500', textColor: 'text-red-500', variant: 'destructive' },
};
