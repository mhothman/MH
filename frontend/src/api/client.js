/**
 * API Client - Base configuration and utilities
 */

const API_URL = process.env.REACT_APP_BACKEND_URL || '';

// Track 401 errors to prevent aggressive logout on race conditions
let consecutiveAuthErrors = 0;
let authErrorResetTimeout = null;
let isRedirecting = false;

/**
 * Get authentication headers
 */
export const getAuthHeaders = () => {
  const token = localStorage.getItem('proflow_token');
  return {
    'Content-Type': 'application/json',
    ...(token && { Authorization: `Bearer ${token}` }),
  };
};

/**
 * Reset auth error counter
 */
const resetAuthErrors = () => {
  consecutiveAuthErrors = 0;
};

/**
 * Handle API response
 */
export const handleResponse = async (response) => {
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    const err = new Error(error.detail?.message || error.detail || 'Request failed');
    err.response = { status: response.status, data: error };
    err.status = response.status;
    
    // Handle token expiration
    if (response.status === 401) {
      consecutiveAuthErrors++;
      
      // Clear any existing reset timeout
      if (authErrorResetTimeout) {
        clearTimeout(authErrorResetTimeout);
      }
      
      // Reset counter after 5 seconds of no 401s
      authErrorResetTimeout = setTimeout(resetAuthErrors, 5000);
      
      const currentPath = window.location.pathname;
      const isAuthPage = currentPath.includes('/login') || currentPath.includes('/register');
      
      // Only redirect if:
      // 1. Not already on auth page
      // 2. Had multiple consecutive 401s (not just a race condition)
      // 3. Not already redirecting
      if (!isAuthPage && consecutiveAuthErrors >= 2 && !isRedirecting) {
        isRedirecting = true;
        // Clear expired token
        localStorage.removeItem('proflow_token');
        localStorage.removeItem('proflow_user');
        localStorage.removeItem('proflow_current_org');
        localStorage.removeItem('proflow_branding');
        // Redirect to login
        setTimeout(() => {
          window.location.href = '/login?expired=true';
        }, 300);
      }
    } else {
      // Reset counter on non-401 errors (server is responding)
      resetAuthErrors();
    }
    
    throw err;
  }
  
  // Success - reset auth error counter
  resetAuthErrors();
  return response.json();
};

/**
 * Generic GET request
 */
export const get = async (endpoint) => {
  const response = await fetch(`${API_URL}${endpoint}`, {
    headers: getAuthHeaders(),
    credentials: 'include',
  });
  return handleResponse(response);
};

/**
 * Generic POST request
 */
export const post = async (endpoint, data) => {
  const response = await fetch(`${API_URL}${endpoint}`, {
    method: 'POST',
    headers: getAuthHeaders(),
    credentials: 'include',
    body: JSON.stringify(data),
  });
  return handleResponse(response);
};

/**
 * Generic PUT request
 */
export const put = async (endpoint, data) => {
  const response = await fetch(`${API_URL}${endpoint}`, {
    method: 'PUT',
    headers: getAuthHeaders(),
    credentials: 'include',
    body: JSON.stringify(data),
  });
  return handleResponse(response);
};

/**
 * Generic DELETE request
 */
export const del = async (endpoint) => {
  const response = await fetch(`${API_URL}${endpoint}`, {
    method: 'DELETE',
    headers: getAuthHeaders(),
    credentials: 'include',
  });
  return handleResponse(response);
};

/**
 * Generic PATCH request
 */
export const patch = async (endpoint, data) => {
  const response = await fetch(`${API_URL}${endpoint}`, {
    method: 'PATCH',
    headers: getAuthHeaders(),
    credentials: 'include',
    body: JSON.stringify(data),
  });
  return handleResponse(response);
};

/**
 * File upload request
 */
export const uploadFile = async (endpoint, file, fieldName = 'file') => {
  const token = localStorage.getItem('proflow_token');
  const formData = new FormData();
  formData.append(fieldName, file);
  
  const response = await fetch(`${API_URL}${endpoint}`, {
    method: 'POST',
    headers: {
      ...(token && { Authorization: `Bearer ${token}` }),
    },
    credentials: 'include',
    body: formData,
  });
  return handleResponse(response);
};

export { API_URL };
