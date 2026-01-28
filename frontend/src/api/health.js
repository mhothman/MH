/**
 * Health API - Database health and performance monitoring endpoints
 */
import { get, post } from './client';

// ==================== Database Health ====================

export const getDatabaseHealth = async () => {
  return get('/api/health/db');
};

export const getQueryStats = async () => {
  return get('/api/health/db/stats');
};

export const resetQueryStats = async () => {
  return post('/api/health/db/stats/reset', {});
};

// ==================== Indexes ====================

export const getIndexInfo = async () => {
  return get('/api/health/db/indexes');
};

export const createRecommendedIndexes = async () => {
  return post('/api/health/db/indexes/create', {});
};

// ==================== Collections ====================

export const getCollectionStats = async () => {
  return get('/api/health/db/collections');
};

export const getSlowQueries = async () => {
  return get('/api/health/db/slow-queries');
};
