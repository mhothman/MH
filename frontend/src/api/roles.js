/**
 * Roles API - Custom role management endpoints
 */
import { get, post, put, del } from './client';

// ==================== Permissions ====================

export const getAllPermissions = async () => {
  return get('/api/roles/permissions');
};

// ==================== Roles ====================

export const getRoles = async (orgId) => {
  return get(`/api/roles/org/${orgId}`);
};

export const createCustomRole = async (orgId, data) => {
  return post(`/api/roles/org/${orgId}`, data);
};

export const updateCustomRole = async (roleId, data) => {
  return put(`/api/roles/${roleId}`, data);
};

export const deleteCustomRole = async (roleId) => {
  return del(`/api/roles/${roleId}`);
};

export const updateBuiltInRole = async (orgId, roleName, roleData) => {
  return put(`/api/roles/builtin/${roleName}/org/${orgId}`, roleData);
};

export const duplicateRole = async (roleId, newName) => {
  return post(`/api/roles/${roleId}/duplicate`, { name: newName });
};

export const getRoleMembers = async (roleId) => {
  return get(`/api/roles/${roleId}/members`);
};
