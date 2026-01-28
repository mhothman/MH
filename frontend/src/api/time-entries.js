/**
 * Time Entries API - All time tracking endpoints
 */
import { get, post, del } from './client';

// ==================== Time Entries ====================

export const getTimeEntries = async (taskId = null, filters = {}) => {
  const params = new URLSearchParams();
  if (taskId) params.append('task_id', taskId);
  if (filters.user_id) params.append('user_id', filters.user_id);
  if (filters.start_date) params.append('start_date', filters.start_date);
  if (filters.end_date) params.append('end_date', filters.end_date);
  
  const url = `/api/time-entries/?${params.toString()}`;
  return get(url);
};

export const createTimeEntry = async (data) => {
  return post('/api/time-entries/', data);
};

export const updateTimeEntry = async (entryId, data) => {
  return post(`/api/time-entries/${entryId}`, data);
};

export const deleteTimeEntry = async (entryId) => {
  return del(`/api/time-entries/${entryId}`);
};

// ==================== Timer ====================

export const startTimer = async (taskId, description = null) => {
  return post('/api/time-entries/timer/start', { task_id: taskId, description });
};

export const stopTimer = async () => {
  return post('/api/time-entries/timer/stop', {});
};

export const getActiveTimer = async () => {
  return get('/api/time-entries/timer/active');
};

export const discardTimer = async () => {
  return post('/api/time-entries/timer/discard', {});
};

// ==================== Time Reports ====================

export const getTimeSummary = async (filters = {}) => {
  const params = new URLSearchParams();
  if (filters.user_id) params.append('user_id', filters.user_id);
  if (filters.project_id) params.append('project_id', filters.project_id);
  if (filters.start_date) params.append('start_date', filters.start_date);
  if (filters.end_date) params.append('end_date', filters.end_date);
  
  return get(`/api/time-entries/summary?${params.toString()}`);
};
