/**
 * Customers API - All customer management endpoints
 */
import { get, post, put, del } from './client';

// ==================== Customers ====================

export const getCustomers = async (orgId) => {
  return get(`/api/customers/?org_id=${orgId}`);
};

export const getCustomer = async (customerId) => {
  return get(`/api/customers/${customerId}`);
};

export const createCustomer = async (orgId, data) => {
  // Map frontend 'contact' field to backend 'phone' field
  const payload = {
    name: data.name,
    email: data.email || null,
    phone: data.contact || null,  // Frontend uses 'contact', backend expects 'phone'
    company: data.company || null,
    address: data.address || null,
    notes: data.notes || null,
  };
  return post(`/api/customers/?org_id=${orgId}`, payload);
};

export const updateCustomer = async (customerId, data) => {
  // Map frontend 'contact' field to backend 'phone' field
  const payload = {
    name: data.name,
    email: data.email || null,
    phone: data.contact || null,  // Frontend uses 'contact', backend expects 'phone'
    company: data.company || null,
    address: data.address || null,
    notes: data.notes || null,
  };
  return put(`/api/customers/${customerId}`, payload);
};

export const deleteCustomer = async (customerId) => {
  return del(`/api/customers/${customerId}`);
};

export const getCustomerProjects = async (customerId) => {
  return get(`/api/customers/${customerId}/projects`);
};

export const getCustomerStats = async (customerId) => {
  return get(`/api/customers/${customerId}/stats`);
};
