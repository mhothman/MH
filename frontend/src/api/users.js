/**
 * User API - User profile management endpoints
 */
import { get, post, put, uploadFile } from './client';

// ==================== User Profile ====================

export const getUser = async (userId) => {
  return get(`/api/users/${userId}`);
};

export const updateProfile = async (data) => {
  return put('/api/auth/profile', data);
};

export const uploadAvatar = async (file) => {
  return uploadFile('/api/auth/avatar', file);
};

export const deleteAvatar = async () => {
  const response = await fetch(`${process.env.REACT_APP_BACKEND_URL}/api/auth/avatar`, {
    method: 'DELETE',
    headers: {
      'Authorization': `Bearer ${localStorage.getItem('proflow_token')}`,
    },
    credentials: 'include',
  });
  if (!response.ok) throw new Error('Failed to delete avatar');
  return response.json();
};

// ==================== User Preferences ====================

export const getPreferences = async () => {
  return get('/api/auth/preferences');
};

export const updatePreferences = async (preferences) => {
  return put('/api/auth/preferences', preferences);
};

// ==================== Admin Password Reset ====================

export const adminResetPassword = async (orgId, userId) => {
  return post(`/api/organizations/${orgId}/members/${userId}/reset-password`, {});
};

// ==================== User Search (for mentions) ====================

export const searchUsersForMention = async (query, projectId) => {
  return get(`/api/users/search?q=${encodeURIComponent(query)}&project_id=${projectId}`);
};
