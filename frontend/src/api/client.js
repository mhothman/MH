/**
 * API Client - Base configuration and utilities
 */

const API_URL = process.env.REACT_APP_BACKEND_URL || '';

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
 * Handle API response
 */
export const handleResponse = async (response) => {
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    const err = new Error(error.detail?.message || error.detail || 'Request failed');
    err.response = { status: response.status, data: error };
    err.status = response.status;
    throw err;
  }
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
