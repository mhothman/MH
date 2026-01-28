/**
 * Dashboard API - Dashboard and analytics endpoints
 */
import { get } from './client';

// ==================== Dashboard ====================

export const getDashboard = async (orgId = null) => {
  const url = orgId 
    ? `/api/dashboard/?org_id=${orgId}`
    : `/api/dashboard/`;
  return get(url);
};

export const getDashboardStats = async (orgId) => {
  return get(`/api/dashboard/stats?org_id=${orgId}`);
};

export const getRecentActivity = async (orgId, limit = 20) => {
  return get(`/api/dashboard/activity?org_id=${orgId}&limit=${limit}`);
};

export const getUpcomingDeadlines = async (orgId, days = 7) => {
  return get(`/api/dashboard/deadlines?org_id=${orgId}&days=${days}`);
};
