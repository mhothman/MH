/**
 * Comments API - All comment-related endpoints
 */
import { get, post, del } from './client';

// ==================== Comments ====================

export const getComments = async (taskId = null, projectId = null) => {
  const params = new URLSearchParams();
  if (taskId) params.append('task_id', taskId);
  if (projectId) params.append('project_id', projectId);
  
  const url = `/api/comments/?${params.toString()}`;
  return get(url);
};

export const createComment = async (data) => {
  return post('/api/comments/', data);
};

export const updateComment = async (commentId, data) => {
  return post(`/api/comments/${commentId}`, data);
};

export const deleteComment = async (commentId) => {
  return del(`/api/comments/${commentId}`);
};
