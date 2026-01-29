/**
 * AppDataContext - Global state for commonly used data
 * Prevents duplicate API calls across components
 */
import { createContext, useContext, useState, useCallback, useEffect, useRef } from 'react';
import { getOrganizations, getMyPermissions } from '../api';
import { getProjects } from '../api/projects';
import { getCustomers } from '../api/customers';
import { useAuth } from './AuthContext';

const AppDataContext = createContext(null);

export const AppDataProvider = ({ children }) => {
  const { user, isAuthenticated } = useAuth();
  
  // Global data state
  const [organizations, setOrganizations] = useState([]);
  const [currentOrgId, setCurrentOrgId] = useState(() => {
    const saved = localStorage.getItem('proflow_current_org');
    if (saved) {
      try {
        return JSON.parse(saved).org_id;
      } catch (e) {
        return null;
      }
    }
    return null;
  });
  const [projects, setProjects] = useState([]);
  const [customers, setCustomers] = useState([]);
  const [permissions, setPermissions] = useState([]);
  
  // Loading states
  const [orgsLoading, setOrgsLoading] = useState(false);
  const [projectsLoading, setProjectsLoading] = useState(false);
  const [customersLoading, setCustomersLoading] = useState(false);
  
  // Track if data has been loaded
  const dataLoadedRef = useRef({
    orgs: false,
    projects: false,
    customers: false,
    permissions: false,
  });
  
  // Prevent duplicate calls
  const loadingRef = useRef({
    orgs: false,
    projects: false,
    customers: false,
    permissions: false,
  });

  // Load organizations
  const loadOrganizations = useCallback(async (force = false) => {
    if (!isAuthenticated) return [];
    if (loadingRef.current.orgs) return organizations;
    if (!force && dataLoadedRef.current.orgs && organizations.length > 0) return organizations;
    
    loadingRef.current.orgs = true;
    setOrgsLoading(true);
    
    try {
      const orgs = await getOrganizations();
      setOrganizations(orgs);
      dataLoadedRef.current.orgs = true;
      
      // Set current org if not set
      if (orgs.length > 0 && !currentOrgId) {
        const orgId = orgs[0].org_id;
        setCurrentOrgId(orgId);
        localStorage.setItem('proflow_current_org', JSON.stringify(orgs[0]));
      }
      
      return orgs;
    } catch (error) {
      console.error('Failed to load organizations:', error);
      return [];
    } finally {
      loadingRef.current.orgs = false;
      setOrgsLoading(false);
    }
  }, [isAuthenticated, organizations, currentOrgId]);

  // Load projects
  const loadProjects = useCallback(async (force = false) => {
    if (!isAuthenticated) return [];
    if (loadingRef.current.projects) return projects;
    if (!force && dataLoadedRef.current.projects && projects.length > 0) return projects;
    
    loadingRef.current.projects = true;
    setProjectsLoading(true);
    
    try {
      const projs = await getProjects();
      setProjects(projs);
      dataLoadedRef.current.projects = true;
      return projs;
    } catch (error) {
      console.error('Failed to load projects:', error);
      return [];
    } finally {
      loadingRef.current.projects = false;
      setProjectsLoading(false);
    }
  }, [isAuthenticated, projects]);

  // Load customers for an org
  const loadCustomers = useCallback(async (orgId, force = false) => {
    if (!isAuthenticated || !orgId) return [];
    if (loadingRef.current.customers) return customers;
    if (!force && dataLoadedRef.current.customers && customers.length > 0) return customers;
    
    loadingRef.current.customers = true;
    setCustomersLoading(true);
    
    try {
      const custs = await getCustomers(orgId);
      setCustomers(custs);
      dataLoadedRef.current.customers = true;
      return custs;
    } catch (error) {
      console.error('Failed to load customers:', error);
      return [];
    } finally {
      loadingRef.current.customers = false;
      setCustomersLoading(false);
    }
  }, [isAuthenticated, customers]);

  // Load permissions for an org
  const loadPermissions = useCallback(async (orgId, force = false) => {
    if (!isAuthenticated || !orgId) return [];
    if (loadingRef.current.permissions) return permissions;
    if (!force && dataLoadedRef.current.permissions && permissions.length > 0) return permissions;
    
    loadingRef.current.permissions = true;
    
    try {
      const data = await getMyPermissions(orgId);
      const perms = data.permissions || [];
      setPermissions(perms);
      dataLoadedRef.current.permissions = true;
      return perms;
    } catch (error) {
      console.error('Failed to load permissions:', error);
      return [];
    } finally {
      loadingRef.current.permissions = false;
    }
  }, [isAuthenticated, permissions]);

  // Change current organization
  const switchOrganization = useCallback((org) => {
    setCurrentOrgId(org.org_id);
    localStorage.setItem('proflow_current_org', JSON.stringify(org));
    
    // Reset org-specific data
    dataLoadedRef.current.customers = false;
    dataLoadedRef.current.permissions = false;
    setCustomers([]);
    setPermissions([]);
  }, []);

  // Get current organization object
  const currentOrg = organizations.find(o => o.org_id === currentOrgId) || organizations[0] || null;

  // Refresh all data
  const refreshAll = useCallback(async () => {
    dataLoadedRef.current = {
      orgs: false,
      projects: false,
      customers: false,
      permissions: false,
    };
    
    await Promise.all([
      loadOrganizations(true),
      loadProjects(true),
    ]);
    
    if (currentOrgId) {
      await Promise.all([
        loadCustomers(currentOrgId, true),
        loadPermissions(currentOrgId, true),
      ]);
    }
  }, [loadOrganizations, loadProjects, loadCustomers, loadPermissions, currentOrgId]);

  // Clear data on logout
  const clearData = useCallback(() => {
    setOrganizations([]);
    setProjects([]);
    setCustomers([]);
    setPermissions([]);
    setCurrentOrgId(null);
    dataLoadedRef.current = {
      orgs: false,
      projects: false,
      customers: false,
      permissions: false,
    };
  }, []);

  // Initial load when authenticated
  useEffect(() => {
    if (isAuthenticated && !dataLoadedRef.current.orgs) {
      loadOrganizations();
    }
  }, [isAuthenticated, loadOrganizations]);

  // Load org-specific data when org changes
  useEffect(() => {
    if (isAuthenticated && currentOrgId) {
      loadCustomers(currentOrgId);
      loadPermissions(currentOrgId);
    }
  }, [isAuthenticated, currentOrgId, loadCustomers, loadPermissions]);

  const value = {
    // Data
    organizations,
    currentOrg,
    currentOrgId,
    projects,
    customers,
    permissions,
    
    // Loading states
    orgsLoading,
    projectsLoading,
    customersLoading,
    
    // Actions
    loadOrganizations,
    loadProjects,
    loadCustomers,
    loadPermissions,
    switchOrganization,
    refreshAll,
    clearData,
    
    // Setters for updates
    setProjects,
    setCustomers,
  };

  return (
    <AppDataContext.Provider value={value}>
      {children}
    </AppDataContext.Provider>
  );
};

export const useAppData = () => {
  const context = useContext(AppDataContext);
  if (!context) {
    throw new Error('useAppData must be used within AppDataProvider');
  }
  return context;
};

export default AppDataContext;
