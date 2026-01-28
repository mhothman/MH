/**
 * Automations API - All automation rule endpoints
 */
import { get, post, put, del } from './client';

// ==================== Automations ====================

export const getAutomations = async (orgId) => {
  return get(`/api/automations/org/${orgId}`);
};

export const getAutomation = async (automationId) => {
  return get(`/api/automations/${automationId}`);
};

export const createAutomation = async (orgId, data) => {
  return post(`/api/automations/org/${orgId}`, data);
};

export const updateAutomation = async (automationId, data) => {
  return put(`/api/automations/${automationId}`, data);
};

export const deleteAutomation = async (automationId) => {
  return del(`/api/automations/${automationId}`);
};

export const toggleAutomation = async (automationId, enabled) => {
  return put(`/api/automations/${automationId}`, { enabled });
};

export const getAutomationHistory = async (automationId, limit = 50) => {
  return get(`/api/automations/${automationId}/history?limit=${limit}`);
};

// ==================== Automation Metadata ====================

export const getTriggerTypes = async () => {
  return get('/api/automations/triggers');
};

export const getActionTypes = async () => {
  return get('/api/automations/actions');
};

export const testAutomation = async (automationId) => {
  return post(`/api/automations/${automationId}/test`, {});
};
