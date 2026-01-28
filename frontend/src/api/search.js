/**
 * Search API - Global search endpoints
 */
import { get } from './client';

// ==================== Search ====================

export const globalSearch = async (query, orgId = null, types = ['projects', 'tasks', 'comments']) => {
  const params = new URLSearchParams({ q: query });
  if (orgId) params.append('org_id', orgId);
  types.forEach(t => params.append('types', t));
  
  return get(`/api/search?${params.toString()}`);
};

export const searchTasks = async (query, projectId = null) => {
  const params = new URLSearchParams({ q: query });
  if (projectId) params.append('project_id', projectId);
  
  return get(`/api/search/tasks?${params.toString()}`);
};

export const searchProjects = async (query, orgId = null) => {
  const params = new URLSearchParams({ q: query });
  if (orgId) params.append('org_id', orgId);
  
  return get(`/api/search/projects?${params.toString()}`);
};

export const searchUsers = async (query, orgId) => {
  const params = new URLSearchParams({ q: query, org_id: orgId });
  
  return get(`/api/search/users?${params.toString()}`);
};
