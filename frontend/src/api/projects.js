/**
 * Projects API - All project-related endpoints
 */
import { get, post, put, del } from './client';

// ==================== Projects ====================

export const getProjects = async (orgId = null) => {
  const url = orgId 
    ? `/api/projects/?org_id=${orgId}`
    : `/api/projects/`;
  return get(url);
};

export const getProject = async (projectId) => {
  return get(`/api/projects/${projectId}`);
};

export const createProject = async (orgId, projectData) => {
  return post(`/api/projects/?org_id=${orgId}`, projectData);
};

export const updateProject = async (projectId, data) => {
  return put(`/api/projects/${projectId}`, data);
};

export const deleteProject = async (projectId) => {
  return del(`/api/projects/${projectId}`);
};

export const getProjectMembers = async (projectId) => {
  return get(`/api/projects/${projectId}/members`);
};

export const addProjectMember = async (projectId, userId, role) => {
  return post(`/api/projects/${projectId}/members`, { user_id: userId, role });
};

export const removeProjectMember = async (projectId, userId) => {
  return del(`/api/projects/${projectId}/members/${userId}`);
};

export const getProjectStatuses = async (projectId) => {
  return get(`/api/projects/${projectId}/statuses`);
};

export const updateProjectStatuses = async (projectId, statuses) => {
  return put(`/api/projects/${projectId}/statuses`, { statuses });
};

export const updateTaskOrder = async (projectId, taskOrder) => {
  return put(`/api/projects/${projectId}/task-order`, { task_order: taskOrder });
};
