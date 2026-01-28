/**
 * Organizations API - All organization-related endpoints
 */
import { get, post, put, del } from './client';

// ==================== Organizations ====================

export const getOrganizations = async () => {
  return get('/api/organizations/');
};

export const getOrganization = async (orgId) => {
  return get(`/api/organizations/${orgId}`);
};

export const createOrganization = async (orgData) => {
  return post('/api/organizations/', orgData);
};

export const updateOrganization = async (orgId, data) => {
  return put(`/api/organizations/${orgId}`, data);
};

export const getOrganizationMembers = async (orgId) => {
  return get(`/api/organizations/${orgId}/members`);
};

// ==================== Invitations ====================

export const inviteUser = async (orgId, email, role) => {
  return post(`/api/organizations/${orgId}/invite`, { email, role });
};

export const getInvitations = async (orgId) => {
  return get(`/api/organizations/${orgId}/invitations`);
};

export const cancelInvitation = async (orgId, invitationId) => {
  return del(`/api/organizations/${orgId}/invitations/${invitationId}`);
};

export const resendInvitation = async (orgId, invitationId) => {
  return post(`/api/organizations/${orgId}/invitations/${invitationId}/resend`, {});
};

// ==================== Member Management ====================

export const removeMember = async (orgId, userId) => {
  return del(`/api/organizations/${orgId}/members/${userId}`);
};

export const updateMemberRole = async (orgId, userId, role) => {
  return put(`/api/organizations/${orgId}/members/${userId}/role`, { role });
};

export const suspendMember = async (orgId, userId) => {
  return post(`/api/organizations/${orgId}/members/${userId}/suspend`, {});
};

export const unsuspendMember = async (orgId, userId) => {
  return post(`/api/organizations/${orgId}/members/${userId}/unsuspend`, {});
};

// ==================== Additional Member Management ====================

export const changeMemberRole = async (orgId, userId, role, customRoleId = null) => {
  const body = customRoleId ? { role: null, custom_role_id: customRoleId } : { role };
  return post(`/api/organizations/${orgId}/members/${userId}/change-role`, body);
};

export const inviteMember = async (orgId, data) => {
  return post(`/api/organizations/${orgId}/invite`, data);
};

export const getPendingInvitations = async (orgId) => {
  return get(`/api/organizations/${orgId}/invitations`);
};

export const resendInvitationByEmail = async (orgId, email) => {
  return post(`/api/organizations/${orgId}/invitations/resend?email=${encodeURIComponent(email)}`, {});
};
