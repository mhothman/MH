/**
 * Tasks API - All task-related endpoints
 */
import { get, post, put, del, uploadFile, API_URL, getAuthHeaders } from './client';

// ==================== Tasks ====================

export const getTasks = async (projectId = null) => {
  const url = projectId ? `/api/tasks/?project_id=${projectId}` : '/api/tasks/';
  return get(url);
};

export const getTask = async (taskId) => {
  return get(`/api/tasks/${taskId}`);
};

export const createTask = async (taskData) => {
  return post('/api/tasks/', taskData);
};

export const updateTask = async (taskId, data) => {
  return put(`/api/tasks/${taskId}`, data);
};

export const deleteTask = async (taskId) => {
  return del(`/api/tasks/${taskId}`);
};

// ==================== Bulk Operations ====================

export const bulkUpdateTasks = async (taskIds, updates) => {
  return post('/api/tasks/bulk/update', { task_ids: taskIds, updates });
};

export const bulkAssignTasks = async (taskIds, assigneeId) => {
  return post('/api/tasks/bulk/assign', { task_ids: taskIds, assignee_id: assigneeId });
};

export const bulkDeleteTasks = async (taskIds) => {
  return post('/api/tasks/bulk/delete', { task_ids: taskIds });
};

// ==================== Checklist ====================

export const addChecklistItem = async (taskId, title) => {
  return post(`/api/tasks/${taskId}/checklist`, { title, completed: false });
};

export const updateChecklistItem = async (taskId, itemId, data) => {
  return put(`/api/tasks/${taskId}/checklist/${itemId}`, data);
};

export const deleteChecklistItem = async (taskId, itemId) => {
  return del(`/api/tasks/${taskId}/checklist/${itemId}`);
};

// ==================== Dependencies ====================

export const addDependency = async (taskId, dependsOnId) => {
  return post(`/api/tasks/${taskId}/dependencies`, { depends_on_id: dependsOnId });
};

export const removeDependency = async (taskId, dependsOnId) => {
  return del(`/api/tasks/${taskId}/dependencies/${dependsOnId}`);
};

export const getTaskDependencies = async (taskId) => {
  return get(`/api/tasks/${taskId}/dependencies`);
};

export const getDependencyGraph = async (projectId) => {
  return get(`/api/tasks/dependency-graph/${projectId}`);
};

// ==================== Attachments ====================

export const uploadAttachment = async (taskId, file) => {
  return uploadFile(`/api/tasks/${taskId}/attachments`, file);
};

export const getAttachments = async (taskId) => {
  return get(`/api/tasks/${taskId}/attachments`);
};

export const deleteAttachment = async (taskId, attachmentId) => {
  return del(`/api/tasks/${taskId}/attachments/${attachmentId}`);
};

export const downloadAttachment = async (taskId, attachmentId) => {
  const response = await fetch(`${API_URL}/api/tasks/${taskId}/attachments/${attachmentId}/download`, {
    headers: getAuthHeaders(),
    credentials: 'include',
  });
  if (!response.ok) throw new Error('Download failed');
  return response.blob();
};

// ==================== Activity ====================

export const getTaskActivity = async (taskId) => {
  return get(`/api/tasks/${taskId}/activity`);
};

// ==================== Recurring ====================

export const generateRecurringTasks = async (taskId) => {
  return post(`/api/tasks/${taskId}/generate-recurring`, {});
};
