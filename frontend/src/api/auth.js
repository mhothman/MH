/**
 * Auth API - Authentication and user management endpoints
 */
import { get, post, API_URL, getAuthHeaders, handleResponse } from './client';

// ==================== Authentication ====================

export const login = async (email, password) => {
  return post('/api/auth/login', { email, password });
};

export const register = async (data) => {
  return post('/api/auth/register', data);
};

export const logout = async () => {
  return post('/api/auth/logout', {});
};

export const getMe = async () => {
  return get('/api/auth/me');
};

export const refreshToken = async () => {
  return post('/api/auth/refresh', {});
};

// ==================== Password Management ====================

export const forgotPassword = async (email) => {
  return post('/api/auth/forgot-password', { email });
};

export const resetPassword = async (token, newPassword) => {
  return post('/api/auth/reset-password', { token, new_password: newPassword });
};

export const changePassword = async (currentPassword, newPassword) => {
  return post('/api/auth/change-password', { 
    current_password: currentPassword, 
    new_password: newPassword 
  });
};

// ==================== Permissions ====================

export const getMyPermissions = async (orgId) => {
  return get(`/api/auth/permissions/${orgId}`);
};

export const getAllRoles = async () => {
  return get('/api/auth/roles');
};

// ==================== Google OAuth ====================

export const googleLogin = async () => {
  return get('/api/auth/google/login');
};

export const googleCallback = async (code) => {
  return post('/api/auth/google/callback', { code });
};

// Helper function - Check if user has a specific permission
export const hasPermission = (permissions, permission) => {
  if (!permissions || !Array.isArray(permissions)) return false;
  return permissions.includes(permission);
};

// Permission constants (should match backend)
export const Permission = {
  PROJECT_VIEW: "project:view",
  PROJECT_CREATE: "project:create",
  PROJECT_EDIT: "project:edit",
  PROJECT_DELETE: "project:delete",
  TASK_VIEW: "task:view",
  TASK_CREATE: "task:create",
  TASK_EDIT: "task:edit",
  TASK_EDIT_OWN: "task:edit_own",
  TASK_DELETE: "task:delete",
  TASK_ASSIGN: "task:assign",
  TASK_CHANGE_STATUS: "task:change_status",
  MEMBER_VIEW: "member:view",
  MEMBER_INVITE: "member:invite",
  MEMBER_REMOVE: "member:remove",
  MEMBER_CHANGE_ROLE: "member:change_role",
  MEMBER_SUSPEND: "member:suspend",
  CUSTOMER_VIEW: "customer:view",
  CUSTOMER_CREATE: "customer:create",
  CUSTOMER_EDIT: "customer:edit",
  CUSTOMER_DELETE: "customer:delete",
  REPORT_VIEW: "report:view",
  REPORT_EXPORT: "report:export",
  REPORT_EXECUTIVE: "report:executive",
  SETTINGS_VIEW: "settings:view",
  SETTINGS_EDIT: "settings:edit",
  AUTOMATION_VIEW: "automation:view",
  AUTOMATION_CREATE: "automation:create",
  AUTOMATION_EDIT: "automation:edit",
  AUTOMATION_DELETE: "automation:delete",
  AUDIT_VIEW: "audit:view",
  AUDIT_EXPORT: "audit:export",
  COMMENT_VIEW: "comment:view",
  COMMENT_CREATE: "comment:create",
  COMMENT_EDIT_OWN: "comment:edit_own",
  COMMENT_DELETE_ANY: "comment:delete_any",
  TIME_VIEW_OWN: "time:view_own",
  TIME_VIEW_ALL: "time:view_all",
  TIME_CREATE: "time:create",
  TIME_EDIT_OWN: "time:edit_own",
  // Workflow permissions
  WORKFLOW_VIEW: "workflow:view",
  WORKFLOW_CREATE: "workflow:create",
  WORKFLOW_EDIT: "workflow:edit",
  WORKFLOW_DELETE: "workflow:delete",
  WORKFLOW_ASSIGN: "workflow:assign",
  // Approval permissions
  APPROVAL_VIEW: "approval:view",
  APPROVAL_REQUEST: "approval:request",
  APPROVAL_APPROVE: "approval:approve",
  APPROVAL_REJECT: "approval:reject",
  APPROVAL_FORCE: "approval:force",
  // Document permissions
  DOCUMENT_VIEW: "document:view",
  DOCUMENT_CREATE: "document:create",
  DOCUMENT_EDIT: "document:edit",
  DOCUMENT_DELETE: "document:delete",
  DOCUMENT_CHANGE_STATUS: "document:change_status",
  DOCUMENT_APPROVE: "document:approve",
  // Budget permissions
  BUDGET_VIEW: "budget:view",
  BUDGET_CREATE: "budget:create",
  BUDGET_EDIT: "budget:edit",
  BUDGET_DELETE: "budget:delete",
  BUDGET_APPROVE: "budget:approve",
  BUDGET_OVERRIDE: "budget:override",
  // Expense permissions
  EXPENSE_VIEW: "expense:view",
  EXPENSE_CREATE: "expense:create",
  EXPENSE_EDIT: "expense:edit",
  EXPENSE_DELETE: "expense:delete",
  EXPENSE_APPROVE: "expense:approve",
};
