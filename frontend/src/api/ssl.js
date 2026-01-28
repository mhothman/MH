/**
 * SSL API - SSL certificate management endpoints
 */
import { get, post, del } from './client';

// ==================== SSL Certificate Management ====================

/**
 * Request a new SSL certificate for organization's custom domain
 */
export const requestSSLCertificate = async (orgId, domain, email = null) => {
  return post(`/api/ssl/org/${orgId}/request`, { domain, email });
};

/**
 * Get SSL certificate status for organization
 */
export const getSSLStatus = async (orgId) => {
  return get(`/api/ssl/org/${orgId}/status`);
};

/**
 * Manually trigger SSL certificate renewal
 */
export const renewSSLCertificate = async (orgId) => {
  return post(`/api/ssl/org/${orgId}/renew`, {});
};

/**
 * Revoke SSL certificate
 */
export const revokeSSLCertificate = async (orgId) => {
  return del(`/api/ssl/org/${orgId}/revoke`);
};

/**
 * Get nginx configuration for SSL
 */
export const getNginxConfig = async (orgId) => {
  return get(`/api/ssl/org/${orgId}/nginx-config`);
};

/**
 * Toggle auto-renewal for SSL certificate
 */
export const toggleSSLAutoRenew = async (orgId, enabled) => {
  return post(`/api/ssl/org/${orgId}/toggle-auto-renew?enabled=${enabled}`, {});
};

// ==================== Admin Endpoints ====================

/**
 * Get all SSL certificates (Super Admin only)
 */
export const getAllSSLCertificates = async () => {
  return get('/api/ssl/admin/all-certificates');
};

/**
 * Renew all expiring certificates (Super Admin only)
 */
export const renewExpiringCertificates = async () => {
  return post('/api/ssl/admin/renew-expiring', {});
};
