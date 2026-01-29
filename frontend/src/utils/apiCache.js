/**
 * API Cache - Prevents duplicate API calls and caches responses
 */

const cache = new Map();
const pendingRequests = new Map();
const CACHE_TTL = 30000; // 30 seconds cache

/**
 * Get cached data or fetch from API
 */
export const cachedFetch = async (key, fetchFn, ttl = CACHE_TTL) => {
  // Check if we have a valid cached response
  const cached = cache.get(key);
  if (cached && Date.now() - cached.timestamp < ttl) {
    return cached.data;
  }

  // Check if there's already a pending request for this key
  if (pendingRequests.has(key)) {
    return pendingRequests.get(key);
  }

  // Create new request
  const request = fetchFn()
    .then((data) => {
      cache.set(key, { data, timestamp: Date.now() });
      pendingRequests.delete(key);
      return data;
    })
    .catch((error) => {
      pendingRequests.delete(key);
      throw error;
    });

  pendingRequests.set(key, request);
  return request;
};

/**
 * Invalidate cache for a specific key or pattern
 */
export const invalidateCache = (keyOrPattern) => {
  if (typeof keyOrPattern === 'string') {
    cache.delete(keyOrPattern);
  } else if (keyOrPattern instanceof RegExp) {
    for (const key of cache.keys()) {
      if (keyOrPattern.test(key)) {
        cache.delete(key);
      }
    }
  }
};

/**
 * Clear all cache
 */
export const clearCache = () => {
  cache.clear();
  pendingRequests.clear();
};

/**
 * Get cache stats (for debugging)
 */
export const getCacheStats = () => ({
  cacheSize: cache.size,
  pendingRequests: pendingRequests.size,
  keys: Array.from(cache.keys()),
});
