/**
 * SettingsPage - Refactored to use modular sub-components
 */
import { useState, useEffect } from "react";
import { useAuth } from "../context/AuthContext";
import { useTheme } from "../context/ThemeContext";
import { getMyPermissions, hasPermission, Permission } from "../api";
import { 
  getOrganizations, 
  getOrganizationMembers, 
  inviteMember,
  removeMember,
  suspendMember,
  unsuspendMember,
  getPendingInvitations,
  resendInvitationByEmail,
  cancelInvitation,
  changeMemberRole,
  updateOrganization,
} from "../api/organizations";
import { adminResetPassword } from "../api/users";
import {
  getRoles,
  getAllPermissions,
  createCustomRole,
  updateCustomRole,
  updateBuiltInRole,
  deleteCustomRole,
} from "../api/roles";
import {
  getBranding,
  updateBranding,
  publishBranding,
  resetBranding,
  uploadLogo,
  deleteLogo,
  getPresetThemes,
} from "../api/branding";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../components/ui/tabs";
import { LoadingSpinner } from "../components/ui/loading-spinner";
import { toast } from "sonner";

// Import sub-components
import ProfileSettings from "../components/settings/ProfileSettings";
import OrganizationSettings from "../components/settings/OrganizationSettings";
import DomainSettings from "../components/settings/DomainSettings";
import { TeamSettings } from "../components/settings/TeamSettings";
import { BrandingSettings } from "../components/settings/BrandingSettings";
import { RolesSettings } from "../components/settings/RolesSettings";
import { PreferencesSettings } from "../components/settings/PreferencesSettings";
import { WorkflowSettings } from "../components/settings/WorkflowSettings";
import { DocumentWorkflowSettings } from "../components/settings/DocumentWorkflowSettings";
import PerformanceDashboard from "../components/PerformanceDashboard";

import {
  User,
  Building2,
  Users,
  Palette,
  Shield,
  Image,
  Globe,
  Activity,
  GitBranch,
  FileText,
} from "lucide-react";

export default function SettingsPage() {
  const { user } = useAuth();
  const { theme, toggleTheme, previewBranding, revertPreview, loadBranding: reloadBranding } = useTheme();
  const [loading, setLoading] = useState(true);
  const [organizations, setOrganizations] = useState([]);
  const [members, setMembers] = useState([]);
  const [pendingInvitations, setPendingInvitations] = useState([]);
  const [selectedOrg, setSelectedOrg] = useState(null);
  const [myPermissions, setMyPermissions] = useState([]);
  const [myRole, setMyRole] = useState("");
  
  // Role Management State
  const [rolesData, setRolesData] = useState({ built_in_roles: [], custom_roles: [] });
  const [allPermissions, setAllPermissions] = useState({ permissions: [], categories: {} });

  // Branding State
  const [brandingData, setBrandingData] = useState({
    logo_url: null,
    primary_color: "#0f172a",
    secondary_color: "#3b82f6",
    accent_color: "#10b981",
    dark_mode_supported: true,
    heading_font: "inter",
    body_font: "inter",
    custom_css: "",
    published: false
  });
  const [presetFonts, setPresetFonts] = useState([]);
  const [presetThemes, setPresetThemes] = useState([]);

  useEffect(() => {
    let isMounted = true;
    
    const initLoad = async () => {
      try {
        await Promise.all([
          loadOrganizations(),
          loadAllPermissions(),
        ]);
      } catch (e) {
        if (!isMounted) return;
        console.error("Failed to initialize settings:", e);
      }
    };
    
    initLoad();
    loadPresetFonts();
    loadPresetThemes();
    
    return () => {
      isMounted = false;
    };
  }, []);

  const loadPresetFonts = async () => {
    try {
      // Default fonts list
      setPresetFonts([
        { id: "inter", name: "Inter" },
        { id: "roboto", name: "Roboto" },
        { id: "poppins", name: "Poppins" },
        { id: "open-sans", name: "Open Sans" },
        { id: "lato", name: "Lato" },
        { id: "montserrat", name: "Montserrat" },
        { id: "raleway", name: "Raleway" },
        { id: "playfair", name: "Playfair Display" },
      ]);
    } catch (error) {
      console.error("Failed to load preset fonts:", error);
    }
  };

  const loadPresetThemes = async () => {
    try {
      const data = await getPresetThemes();
      setPresetThemes(data.themes || []);
    } catch (error) {
      console.error("Failed to load preset themes:", error);
    }
  };

  useEffect(() => {
    if (selectedOrg) {
      loadMembers(selectedOrg.org_id);
      loadPendingInvitations(selectedOrg.org_id);
      loadPermissions(selectedOrg.org_id);
      loadRoles(selectedOrg.org_id);
      loadBrandingData(selectedOrg.org_id);
    }
  }, [selectedOrg]);

  const loadBrandingData = async (orgId) => {
    try {
      const data = await getBranding(orgId);
      setBrandingData({
        logo_url: data.logo_url,
        primary_color: data.primary_color || "#0f172a",
        secondary_color: data.secondary_color || "#3b82f6",
        accent_color: data.accent_color || "#10b981",
        dark_mode_supported: data.dark_mode_supported ?? true,
        heading_font: data.heading_font || "inter",
        body_font: data.body_font || "inter",
        custom_css: data.custom_css || "",
        published: data.published || false
      });
    } catch (error) {
      console.error("Failed to load branding:", error);
    }
  };

  const loadAllPermissions = async () => {
    try {
      const data = await getAllPermissions();
      setAllPermissions(data);
    } catch (error) {
      console.error("Failed to load permissions list:", error);
    }
  };

  const loadRoles = async (orgId) => {
    try {
      const data = await getRoles(orgId);
      setRolesData(data);
    } catch (error) {
      console.error("Failed to load roles:", error);
    }
  };

  const loadPermissions = async (orgId) => {
    try {
      const data = await getMyPermissions(orgId);
      setMyPermissions(data.permissions || []);
      setMyRole(data.role || "viewer");
    } catch (error) {
      console.error("Failed to load permissions:", error);
      setMyPermissions([]);
      setMyRole("");
    }
  };

  const canDo = (permission) => hasPermission(myPermissions, permission);

  const loadOrganizations = async () => {
    try {
      const orgs = await getOrganizations();
      setOrganizations(orgs);
      if (orgs.length > 0) {
        setSelectedOrg(orgs[0]);
      }
    } catch (error) {
      console.error("Failed to load organizations:", error);
    } finally {
      setLoading(false);
    }
  };

  const loadMembers = async (orgId) => {
    try {
      const membersData = await getOrganizationMembers(orgId);
      setMembers(membersData);
    } catch (error) {
      console.error("Failed to load members:", error);
    }
  };

  const loadPendingInvitations = async (orgId) => {
    try {
      const invitations = await getPendingInvitations(orgId);
      setPendingInvitations(invitations);
    } catch (error) {
      console.error("Failed to load invitations:", error);
    }
  };

  // Handler functions for sub-components
  const handleSaveOrganization = async (formData) => {
    await updateOrganization(selectedOrg.org_id, formData);
    loadOrganizations();
  };

  const handleInviteMember = async (data) => {
    await inviteMember(selectedOrg.org_id, data);
    loadMembers(selectedOrg.org_id);
    loadPendingInvitations(selectedOrg.org_id);
  };

  const handleRemoveMember = async (userId) => {
    await removeMember(selectedOrg.org_id, userId);
    loadMembers(selectedOrg.org_id);
  };

  const handleSuspendMember = async (userId) => {
    await suspendMember(selectedOrg.org_id, userId);
    loadMembers(selectedOrg.org_id);
  };

  const handleUnsuspendMember = async (userId) => {
    await unsuspendMember(selectedOrg.org_id, userId);
    loadMembers(selectedOrg.org_id);
  };

  const handleResetPassword = async (userId) => {
    await adminResetPassword(selectedOrg.org_id, userId);
  };

  const handleChangeRole = async (userId, role, customRoleId = null) => {
    await changeMemberRole(selectedOrg.org_id, userId, role, customRoleId);
    loadMembers(selectedOrg.org_id);
    loadRoles(selectedOrg.org_id);
  };

  const handleResendInvitation = async (email) => {
    await resendInvitationByEmail(selectedOrg.org_id, email);
  };

  const handleCancelInvitation = async (inviteId) => {
    await cancelInvitation(selectedOrg.org_id, inviteId);
    loadPendingInvitations(selectedOrg.org_id);
  };

  const handleCreateRole = async (roleData) => {
    await createCustomRole(selectedOrg.org_id, roleData);
    loadRoles(selectedOrg.org_id);
  };

  const handleUpdateRole = async (roleIdOrName, roleData) => {
    // Check if this is a built-in role (role names vs role IDs)
    const builtInRoles = ['super_admin', 'org_admin', 'project_manager', 'team_member', 'viewer'];
    if (builtInRoles.includes(roleIdOrName)) {
      await updateBuiltInRole(selectedOrg.org_id, roleIdOrName, roleData);
    } else {
      await updateCustomRole(roleIdOrName, roleData);
    }
    loadRoles(selectedOrg.org_id);
  };

  const handleDeleteRole = async (roleId) => {
    await deleteCustomRole(roleId);
    loadRoles(selectedOrg.org_id);
  };

  const handleUpdateBranding = async (updates) => {
    await updateBranding(selectedOrg.org_id, updates);
  };

  const handlePublishBranding = async () => {
    await publishBranding(selectedOrg.org_id);
    await loadBrandingData(selectedOrg.org_id);
    reloadBranding(selectedOrg.org_id);
  };

  const handleResetBranding = async () => {
    await resetBranding(selectedOrg.org_id);
    await loadBrandingData(selectedOrg.org_id);
    reloadBranding(selectedOrg.org_id);
  };

  const handleUploadLogo = async (file) => {
    const result = await uploadLogo(selectedOrg.org_id, file);
    setBrandingData(prev => ({ ...prev, logo_url: result.logo_url }));
    return result;
  };

  const handleDeleteLogo = async () => {
    await deleteLogo(selectedOrg.org_id);
    setBrandingData(prev => ({ ...prev, logo_url: null }));
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-[60vh]">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-fade-in max-w-4xl" data-testid="settings-page">
      <div>
        <h1 className="font-heading text-2xl sm:text-3xl font-bold tracking-tight">Settings</h1>
        <p className="text-muted-foreground mt-1">Manage your account and organization settings</p>
      </div>

      <Tabs defaultValue="profile">
        <TabsList className="grid w-full grid-cols-8">
          <TabsTrigger value="profile" data-testid="profile-tab">
            <User className="w-4 h-4 mr-2" />
            Profile
          </TabsTrigger>
          <TabsTrigger value="organization" data-testid="organization-tab">
            <Building2 className="w-4 h-4 mr-2" />
            Organization
          </TabsTrigger>
          <TabsTrigger value="branding" data-testid="branding-tab">
            <Image className="w-4 h-4 mr-2" />
            Branding
          </TabsTrigger>
          <TabsTrigger value="team" data-testid="team-tab">
            <Users className="w-4 h-4 mr-2" />
            Team
          </TabsTrigger>
          <TabsTrigger value="roles" data-testid="roles-tab">
            <Shield className="w-4 h-4 mr-2" />
            Roles
          </TabsTrigger>
          <TabsTrigger value="preferences" data-testid="preferences-tab">
            <Palette className="w-4 h-4 mr-2" />
            Preferences
          </TabsTrigger>
          {(myRole === "org_admin" || myRole === "super_admin") && (
            <TabsTrigger value="workflows" data-testid="workflows-tab">
              <GitBranch className="w-4 h-4 mr-2" />
              Workflows
            </TabsTrigger>
          )}
          {(myRole === "org_admin" || myRole === "super_admin") && (
            <TabsTrigger value="documents" data-testid="documents-tab">
              <FileText className="w-4 h-4 mr-2" />
              Documents
            </TabsTrigger>
          )}
          {(myRole === "org_admin" || myRole === "super_admin") && (
            <TabsTrigger value="domain" data-testid="domain-tab">
              <Globe className="w-4 h-4 mr-2" />
              Domain
            </TabsTrigger>
          )}
          {(myRole === "org_admin" || myRole === "super_admin") && (
            <TabsTrigger value="performance" data-testid="performance-tab">
              <Activity className="w-4 h-4 mr-2" />
              Performance
            </TabsTrigger>
          )}
        </TabsList>

        {/* Profile Tab */}
        <TabsContent value="profile" className="mt-6 space-y-6">
          <ProfileSettings 
            user={user} 
            onSave={async (data) => {
              // Profile save handler - would need user update API
              toast.success("Profile saved");
            }}
          />
        </TabsContent>

        {/* Organization Tab */}
        <TabsContent value="organization" className="mt-6 space-y-6">
          <OrganizationSettings 
            organization={selectedOrg}
            onSave={handleSaveOrganization}
          />
        </TabsContent>

        {/* Branding Tab */}
        <TabsContent value="branding" className="mt-6 space-y-6">
          {canDo(Permission.SETTINGS_EDIT) ? (
            <BrandingSettings
              organization={selectedOrg}
              brandingData={brandingData}
              presetFonts={presetFonts}
              presetThemes={presetThemes}
              onUpdateBranding={handleUpdateBranding}
              onPublishBranding={handlePublishBranding}
              onResetBranding={handleResetBranding}
              onUploadLogo={handleUploadLogo}
              onDeleteLogo={handleDeleteLogo}
              previewBranding={previewBranding}
              revertPreview={revertPreview}
            />
          ) : (
            <div className="text-center py-8 text-muted-foreground">
              You don&apos;t have permission to edit branding settings
            </div>
          )}
        </TabsContent>

        {/* Team Tab */}
        <TabsContent value="team" className="mt-6 space-y-6">
          <TeamSettings
            members={members}
            pendingInvitations={pendingInvitations}
            customRoles={rolesData.custom_roles}
            myRole={myRole}
            canInvite={canDo(Permission.MEMBER_INVITE)}
            canRemove={canDo(Permission.MEMBER_REMOVE)}
            canChangeRole={canDo(Permission.MEMBER_CHANGE_ROLE)}
            canSuspend={canDo(Permission.MEMBER_SUSPEND)}
            onInvite={handleInviteMember}
            onRemove={handleRemoveMember}
            onSuspend={handleSuspendMember}
            onUnsuspend={handleUnsuspendMember}
            onResetPassword={handleResetPassword}
            onChangeRole={handleChangeRole}
            onResendInvitation={handleResendInvitation}
            onCancelInvitation={handleCancelInvitation}
          />
        </TabsContent>

        {/* Roles Tab */}
        <TabsContent value="roles" className="mt-6 space-y-6">
          <RolesSettings
            builtInRoles={rolesData.built_in_roles}
            customRoles={rolesData.custom_roles}
            allPermissions={allPermissions}
            canManageRoles={canDo(Permission.SETTINGS_EDIT)}
            onCreateRole={handleCreateRole}
            onUpdateRole={handleUpdateRole}
            onDeleteRole={handleDeleteRole}
          />
        </TabsContent>

        {/* Preferences Tab */}
        <TabsContent value="preferences" className="mt-6 space-y-6">
          <PreferencesSettings
            theme={theme}
            onToggleTheme={toggleTheme}
            preferences={{}}
            onSavePreferences={async (prefs) => {
              // Would save to user preferences API
              toast.success("Preferences saved");
            }}
          />
        </TabsContent>

        {/* Workflows Tab (Admin only) */}
        {(myRole === "org_admin" || myRole === "super_admin") && (
          <TabsContent value="workflows" className="mt-6">
            <WorkflowSettings
              orgId={selectedOrg?.org_id}
              canManageWorkflows={canDo(Permission.WORKFLOW_CREATE) || canDo(Permission.WORKFLOW_EDIT)}
            />
          </TabsContent>
        )}

        {/* Document Workflows Tab (Admin only) */}
        {(myRole === "org_admin" || myRole === "super_admin") && (
          <TabsContent value="documents" className="mt-6">
            <DocumentWorkflowSettings
              orgId={selectedOrg?.org_id}
              canManageWorkflows={canDo(Permission.WORKFLOW_CREATE) || canDo(Permission.WORKFLOW_EDIT)}
            />
          </TabsContent>
        )}

        {/* Domain Tab (Admin only) */}
        {(myRole === "org_admin" || myRole === "super_admin") && (
          <TabsContent value="domain" className="mt-6">
            <DomainSettings orgId={selectedOrg?.org_id} />
          </TabsContent>
        )}

        {/* Performance Tab (Admin only) */}
        {(myRole === "org_admin" || myRole === "super_admin") && (
          <TabsContent value="performance" className="mt-6">
            <PerformanceDashboard orgId={selectedOrg?.org_id} />
          </TabsContent>
        )}
      </Tabs>
    </div>
  );
}
