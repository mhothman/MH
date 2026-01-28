/**
 * API Index - Re-export all API modules
 * 
 * This provides backward compatibility with the monolithic api.js
 * while allowing gradual migration to domain-specific modules.
 */

// Re-export client utilities
export { API_URL, getAuthHeaders, handleResponse, get, post, put, del, patch, uploadFile } from './client';

// Re-export domain modules
export * from './auth';
export * from './projects';
export * from './tasks';
export * from './organizations';
export * from './comments';
export * from './time-entries';
export * from './customers';
export * from './automations';
export * from './reports';
export * from './audit';
export * from './branding';
export * from './roles';
export * from './health';
export * from './notifications';
export * from './search';
export * from './dashboard';
export * from './users';
export * from './websocket';
export * from './ssl';
export * from './workflows';
export * from './documents';
