/**
 * Reports API - All reporting and analytics endpoints
 */
import { get, API_URL, getAuthHeaders } from './client';

// ==================== Executive Dashboard ====================

export const getExecutiveDashboard = async (orgId) => {
  return get(`/api/reports/org/${orgId}/dashboard`);
};

export const getProductivityTrends = async (orgId, days = 30) => {
  return get(`/api/reports/org/${orgId}/productivity?days=${days}`);
};

export const getResourceUtilization = async (orgId) => {
  return get(`/api/reports/org/${orgId}/resource-utilization`);
};

// ==================== Workload Report ====================

export const getWorkloadReport = async (orgId, startDate, endDate) => {
  const params = new URLSearchParams({ 
    org_id: orgId, 
    start_date: startDate, 
    end_date: endDate 
  });
  return get(`/api/reports/workload?${params.toString()}`);
};

// ==================== Timeline/Gantt ====================

export const getTimelineData = async (projectId) => {
  return get(`/api/reports/timeline?project_id=${projectId}`);
};

// ==================== Paginated Reports ====================

export const getPaginatedProjects = async (orgId, page = 1, pageSize = 20, filters = {}) => {
  const params = new URLSearchParams({ page: page.toString(), page_size: pageSize.toString() });
  if (filters.status) params.append('status', filters.status);
  if (filters.search) params.append('search', filters.search);
  
  return get(`/api/reports/org/${orgId}/projects?${params.toString()}`);
};

export const getPaginatedTasks = async (orgId, page = 1, pageSize = 20, filters = {}) => {
  const params = new URLSearchParams({ page: page.toString(), page_size: pageSize.toString() });
  if (filters.project_id) params.append('project_id', filters.project_id);
  if (filters.status) params.append('status', filters.status);
  if (filters.priority) params.append('priority', filters.priority);
  if (filters.assignee_id) params.append('assignee_id', filters.assignee_id);
  if (filters.search) params.append('search', filters.search);
  if (filters.overdue_only) params.append('overdue_only', 'true');
  
  return get(`/api/reports/org/${orgId}/tasks?${params.toString()}`);
};

export const getPaginatedTimeEntries = async (orgId, page = 1, pageSize = 20, filters = {}) => {
  const params = new URLSearchParams({ page: page.toString(), page_size: pageSize.toString() });
  if (filters.user_id) params.append('user_id', filters.user_id);
  if (filters.task_id) params.append('task_id', filters.task_id);
  if (filters.start_date) params.append('start_date', filters.start_date);
  if (filters.end_date) params.append('end_date', filters.end_date);
  
  return get(`/api/reports/org/${orgId}/time-entries?${params.toString()}`);
};

// ==================== Export Functions ====================

export const exportTasksReport = async (orgId, format = 'json', projectId = null, status = null) => {
  const params = new URLSearchParams({ org_id: orgId, format });
  if (projectId) params.append('project_id', projectId);
  if (status) params.append('status', status);
  
  const response = await fetch(`${API_URL}/api/reports/export/tasks?${params.toString()}`, {
    headers: getAuthHeaders(),
    credentials: 'include',
  });
  
  if (format === 'csv') {
    return response.blob();
  }
  if (!response.ok) throw new Error('Export failed');
  return response.json();
};

export const exportTimeReport = async (orgId, startDate, endDate, format = 'json', projectId = null) => {
  const params = new URLSearchParams({ 
    org_id: orgId, 
    start_date: startDate, 
    end_date: endDate, 
    format 
  });
  if (projectId) params.append('project_id', projectId);
  
  const response = await fetch(`${API_URL}/api/reports/export/time?${params.toString()}`, {
    headers: getAuthHeaders(),
    credentials: 'include',
  });
  
  if (format === 'csv') {
    return response.blob();
  }
  if (!response.ok) throw new Error('Export failed');
  return response.json();
};

export const exportProjects = async (orgId, format = 'csv') => {
  const response = await fetch(`${API_URL}/api/reports/org/${orgId}/export/projects?format=${format}`, {
    headers: getAuthHeaders(),
    credentials: 'include',
  });
  
  if (format === 'csv') {
    return response.blob();
  }
  if (!response.ok) throw new Error('Export failed');
  return response.json();
};

export const exportTasks = async (orgId, format = 'csv', projectId = null) => {
  const params = new URLSearchParams({ format });
  if (projectId) params.append('project_id', projectId);
  
  const response = await fetch(`${API_URL}/api/reports/org/${orgId}/export/tasks?${params.toString()}`, {
    headers: getAuthHeaders(),
    credentials: 'include',
  });
  
  if (format === 'csv') {
    return response.blob();
  }
  if (!response.ok) throw new Error('Export failed');
  return response.json();
};

export const exportTimeEntries = async (orgId, format = 'csv', startDate = null, endDate = null) => {
  const params = new URLSearchParams({ format });
  if (startDate) params.append('start_date', startDate);
  if (endDate) params.append('end_date', endDate);
  
  const response = await fetch(`${API_URL}/api/reports/org/${orgId}/export/time-entries?${params.toString()}`, {
    headers: getAuthHeaders(),
    credentials: 'include',
  });
  
  if (format === 'csv') {
    return response.blob();
  }
  if (!response.ok) throw new Error('Export failed');
  return response.json();
};
