/**
 * Audit API - All audit log endpoints
 */
import { get, API_URL, getAuthHeaders } from './client';

// ==================== Audit Logs ====================

export const getAuditLogs = async (orgId, filters = {}) => {
  const params = new URLSearchParams();
  if (filters.userId) params.append('user_id', filters.userId);
  if (filters.action) params.append('action', filters.action);
  if (filters.resourceType) params.append('resource_type', filters.resourceType);
  if (filters.startDate) params.append('start_date', filters.startDate);
  if (filters.endDate) params.append('end_date', filters.endDate);
  if (filters.limit) params.append('limit', filters.limit);
  if (filters.skip) params.append('skip', filters.skip);
  
  return get(`/api/audit/org/${orgId}?${params.toString()}`);
};

export const exportAuditLogs = async (orgId, format = 'json', startDate = null, endDate = null) => {
  const params = new URLSearchParams({ format });
  if (startDate) params.append('start_date', startDate);
  if (endDate) params.append('end_date', endDate);
  
  const response = await fetch(`${API_URL}/api/audit/org/${orgId}/export?${params.toString()}`, {
    headers: getAuthHeaders(),
    credentials: 'include',
  });
  
  if (format === 'csv') {
    return response.blob();
  }
  if (!response.ok) throw new Error('Export failed');
  return response.json();
};

export const getAuditActions = async () => {
  return get('/api/audit/actions');
};

export const getAuditResourceTypes = async () => {
  return get('/api/audit/resource-types');
};
