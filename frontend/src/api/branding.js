/**
 * Branding API - All organization branding and theming endpoints
 */
import { get, post, put, del, uploadFile } from './client';

// ==================== Branding ====================

export const getBranding = async (orgId) => {
  return get(`/api/branding/org/${orgId}`);
};

export const getPublicBranding = async (orgId) => {
  return get(`/api/branding/org/${orgId}/public`);
};

export const updateBranding = async (orgId, data) => {
  return put(`/api/branding/org/${orgId}`, data);
};

export const publishBranding = async (orgId) => {
  return post(`/api/branding/org/${orgId}/publish`, {});
};

export const resetBranding = async (orgId) => {
  return post(`/api/branding/org/${orgId}/reset`, {});
};

// ==================== Logo ====================

export const uploadLogo = async (orgId, file) => {
  return uploadFile(`/api/branding/org/${orgId}/logo`, file);
};

export const deleteLogo = async (orgId) => {
  return del(`/api/branding/org/${orgId}/logo`);
};

// ==================== Fonts & Themes ====================

export const getPresetFonts = async () => {
  return get('/api/branding/fonts');
};

export const getPresetThemes = async () => {
  return get('/api/branding/themes');
};

// ==================== White-Label Domain ====================

export const getDomainConfig = async (orgId) => {
  return get(`/api/orgs/${orgId}/domain`);
};

export const configureDomain = async (orgId, domain) => {
  return post(`/api/orgs/${orgId}/domain`, { custom_domain: domain });
};

export const verifyDomain = async (orgId) => {
  return post(`/api/orgs/${orgId}/domain/verify`, {});
};

export const removeDomain = async (orgId) => {
  return del(`/api/orgs/${orgId}/domain`);
};
