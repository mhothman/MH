/**
 * RolesSettings - Custom role management component
 */
import { useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../ui/card";
import { Button } from "../ui/button";
import { Input } from "../ui/input";
import { Label } from "../ui/label";
import { Badge } from "../ui/badge";
import { Checkbox } from "../ui/checkbox";
import { ScrollArea } from "../ui/scroll-area";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "../ui/dialog";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "../ui/alert-dialog";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "../ui/accordion";
import { LoadingSpinner } from "../ui/loading-spinner";
import { toast } from "sonner";
import {
  Plus,
  Pencil,
  Copy,
  Trash2,
  Lock,
  Shield,
  Info,
  Eye,
} from "lucide-react";

export function RolesSettings({
  builtInRoles = [],
  customRoles = [],
  allPermissions = { permissions: [], categories: {} },
  canManageRoles,
  onCreateRole,
  onUpdateRole,
  onDeleteRole,
}) {
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingRole, setEditingRole] = useState(null);
  const [formData, setFormData] = useState({ name: "", description: "", permissions: [], color: "#6366f1" });
  const [saving, setSaving] = useState(false);
  const [deleteDialog, setDeleteDialog] = useState({ open: false, role: null });
  const [deleting, setDeleting] = useState(false);

  const openCreateDialog = () => {
    setEditingRole(null);
    setFormData({ name: "", description: "", permissions: [], color: "#6366f1" });
    setDialogOpen(true);
  };

  const openEditDialog = (role) => {
    setEditingRole(role);
    setFormData({
      name: role.name,
      description: role.description || "",
      permissions: role.permissions || [],
      color: role.color || "#6366f1"
    });
    setDialogOpen(true);
  };

  const duplicateRole = (role) => {
    setEditingRole(null);
    setFormData({
      name: `${role.name} (Copy)`,
      description: role.description || "",
      permissions: [...(role.permissions || [])],
      color: role.color || "#6366f1"
    });
    setDialogOpen(true);
  };

  const togglePermission = (permId) => {
    setFormData(prev => ({
      ...prev,
      permissions: prev.permissions.includes(permId)
        ? prev.permissions.filter(p => p !== permId)
        : [...prev.permissions, permId]
    }));
  };

  const toggleCategory = (categoryPerms) => {
    const permIds = categoryPerms.map(p => p.id);
    const allSelected = permIds.every(id => formData.permissions.includes(id));
    
    setFormData(prev => ({
      ...prev,
      permissions: allSelected
        ? prev.permissions.filter(p => !permIds.includes(p))
        : [...new Set([...prev.permissions, ...permIds])]
    }));
  };

  const handleSave = async () => {
    if (!formData.name.trim()) {
      toast.error("Please enter a role name");
      return;
    }
    
    setSaving(true);
    try {
      if (editingRole) {
        await onUpdateRole?.(editingRole.role_id, formData);
        toast.success("Role updated successfully");
      } else {
        await onCreateRole?.(formData);
        toast.success("Role created successfully");
      }
      setDialogOpen(false);
    } catch (error) {
      toast.error(error.message || "Failed to save role");
    } finally {
      setSaving(false);
    }
  };

  const handleSaveBuiltInRole = async () => {
    if (!formData.originalRole) return;
    
    setSaving(true);
    try {
      // Update built-in role permissions via API - use key (e.g., "super_admin"), not display name
      await onUpdateRole?.(formData.originalRole.key, {
        permissions: formData.permissions,
        description: formData.description,
        color: formData.color,
      });
      toast.success("Built-in role updated successfully");
      setDialogOpen(false);
    } catch (error) {
      toast.error(error.message || "Failed to update built-in role");
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!deleteDialog.role) return;
    
    setDeleting(true);
    try {
      await onDeleteRole?.(deleteDialog.role.role_id);
      toast.success("Role deleted successfully");
      setDeleteDialog({ open: false, role: null });
    } catch (error) {
      toast.error(error.message || "Failed to delete role");
    } finally {
      setDeleting(false);
    }
  };

  const getRoleColor = (role) => role.color || "#6366f1";

  // Open dialog to view/customize built-in role
  const viewBuiltInRole = (role) => {
    setFormData({
      name: `${role.name.replace(/_/g, ' ')} (Custom)`,
      description: role.description || `Customized version of ${role.name.replace(/_/g, ' ')}`,
      color: getRoleColor(role),
      permissions: role.permissions || [],
      isBuiltInView: true, // Flag to show as "view" mode with option to create custom
      originalRole: role,
    });
    setEditingRole(null);
    setDialogOpen(true);
  };

  // Edit built-in role directly (super admin only)
  const editBuiltInRole = (role) => {
    setFormData({
      name: role.name,
      description: role.description || "",
      color: getRoleColor(role),
      permissions: role.permissions || [],
      isBuiltInEdit: true, // Flag to show as edit mode for built-in role
      originalRole: role,
    });
    setEditingRole(role);
    setDialogOpen(true);
  };

  return (
    <div className="space-y-6">
      {/* Built-in Roles */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Lock className="w-5 h-5" />
            Built-in Roles
          </CardTitle>
          <CardDescription>System-defined roles - click to view permissions or customize</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {builtInRoles.map((role) => (
              <div 
                key={role.name} 
                className="flex items-center justify-between p-3 border rounded-lg hover:bg-accent/50 cursor-pointer transition-colors"
                onClick={() => viewBuiltInRole(role)}
              >
                <div className="flex items-center gap-3">
                  <div
                    className="w-3 h-3 rounded-full"
                    style={{ backgroundColor: getRoleColor(role) }}
                  />
                  <div>
                    <p className="font-medium capitalize">{role.name.replace(/_/g, ' ')}</p>
                    <p className="text-sm text-muted-foreground">
                      {role.description || `Default ${role.name.replace(/_/g, ' ')} permissions`}
                    </p>
                    <p className="text-xs text-muted-foreground mt-0.5">
                      {role.permissions?.length || 0} permissions
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  {canManageRoles && (
                    <Button 
                      variant="ghost" 
                      size="sm" 
                      onClick={(e) => {
                        e.stopPropagation();
                        editBuiltInRole(role);
                      }}
                      title="Edit built-in role permissions"
                    >
                      <Pencil className="w-4 h-4 mr-1" />
                      Edit
                    </Button>
                  )}
                  <Button 
                    variant="ghost" 
                    size="sm" 
                    onClick={(e) => {
                      e.stopPropagation();
                      viewBuiltInRole(role);
                    }}
                  >
                    <Eye className="w-4 h-4 mr-1" />
                    View
                  </Button>
                  {canManageRoles && (
                    <Button 
                      variant="ghost" 
                      size="sm" 
                      onClick={(e) => {
                        e.stopPropagation();
                        duplicateRole(role);
                      }}
                    >
                      <Copy className="w-4 h-4 mr-1" />
                      Duplicate
                    </Button>
                  )}
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Custom Roles */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <Shield className="w-5 h-5" />
              Custom Roles
            </CardTitle>
            <CardDescription>Create custom roles with specific permissions</CardDescription>
          </div>
          {canManageRoles && (
            <Button onClick={openCreateDialog} data-testid="create-role-btn">
              <Plus className="w-4 h-4 mr-2" />
              Create Role
            </Button>
          )}
        </CardHeader>
        <CardContent>
          {customRoles.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              <Shield className="w-12 h-12 mx-auto mb-3 opacity-50" />
              <p>No custom roles yet</p>
              {canManageRoles && (
                <p className="text-sm mt-1">Create a custom role to define specific permissions</p>
              )}
            </div>
          ) : (
            <div className="space-y-3">
              {customRoles.map((role) => (
                <div key={role.role_id} className="flex items-center justify-between p-3 border rounded-lg">
                  <div className="flex items-center gap-3">
                    <div
                      className="w-3 h-3 rounded-full"
                      style={{ backgroundColor: getRoleColor(role) }}
                    />
                    <div>
                      <p className="font-medium">{role.name}</p>
                      <p className="text-sm text-muted-foreground">
                        {role.permissions?.length || 0} permissions
                        {role.member_count > 0 && ` • ${role.member_count} member${role.member_count !== 1 ? 's' : ''}`}
                      </p>
                    </div>
                  </div>
                  {canManageRoles && (
                    <div className="flex items-center gap-1">
                      <Button variant="ghost" size="sm" onClick={() => openEditDialog(role)}>
                        <Pencil className="w-4 h-4" />
                      </Button>
                      <Button variant="ghost" size="sm" onClick={() => duplicateRole(role)}>
                        <Copy className="w-4 h-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        className="text-destructive"
                        onClick={() => setDeleteDialog({ open: true, role })}
                      >
                        <Trash2 className="w-4 h-4" />
                      </Button>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Create/Edit Role Dialog */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-w-2xl max-h-[85vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>
              {formData.isBuiltInView 
                ? `Viewing: ${formData.originalRole?.name?.replace(/_/g, ' ')}`
                : formData.isBuiltInEdit
                  ? `Edit Built-in Role: ${formData.originalRole?.name?.replace(/_/g, ' ')}`
                  : editingRole 
                    ? "Edit Custom Role" 
                    : "Create Custom Role"
              }
            </DialogTitle>
            <DialogDescription>
              {formData.isBuiltInView 
                ? "This is a built-in role. You can view its permissions or create a custom version."
                : formData.isBuiltInEdit
                  ? "Modify the permissions for this built-in role. Changes apply to all users with this role."
                  : "Define role name and select permissions"
              }
            </DialogDescription>
          </DialogHeader>
          
          {formData.isBuiltInView && (
            <div className="flex items-center gap-2 p-3 bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-800 rounded-lg mb-4">
              <Info className="w-4 h-4 text-amber-600" />
              <p className="text-sm text-amber-700 dark:text-amber-400">
                Built-in roles cannot be modified. To customize, click &quot;Create Custom Version&quot; below.
              </p>
            </div>
          )}
          
          <div className="space-y-6 pt-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="role-name">Role Name</Label>
                <Input
                  id="role-name"
                  placeholder="e.g., Senior Developer"
                  value={formData.name}
                  onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
                  data-testid="role-name-input"
                  disabled={formData.isBuiltInView || formData.isBuiltInEdit}
                />
                {formData.isBuiltInEdit && (
                  <p className="text-xs text-muted-foreground">Built-in role names cannot be changed</p>
                )}
              </div>
              <div className="space-y-2">
                <Label>Color</Label>
                <div className="flex items-center gap-2">
                  <input
                    type="color"
                    value={formData.color}
                    onChange={(e) => setFormData(prev => ({ ...prev, color: e.target.value }))}
                    className="w-10 h-10 rounded cursor-pointer border"
                    disabled={formData.isBuiltInView && !formData.customizing}
                  />
                  <Input
                    value={formData.color}
                    onChange={(e) => setFormData(prev => ({ ...prev, color: e.target.value }))}
                    className="w-28 font-mono text-sm"
                    disabled={formData.isBuiltInView && !formData.customizing}
                  />
                </div>
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="role-description">Description (optional)</Label>
              <Input
                id="role-description"
                placeholder="Describe this role's responsibilities"
                value={formData.description}
                onChange={(e) => setFormData(prev => ({ ...prev, description: e.target.value }))}
                disabled={formData.isBuiltInView && !formData.customizing}
              />
            </div>

            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <Label className="text-base">Permissions</Label>
                <Badge variant="secondary">
                  {formData.permissions.length} selected
                </Badge>
              </div>
              
              <ScrollArea className="h-[300px] border rounded-lg p-4">
                <Accordion type="multiple" className="w-full">
                  {Object.entries(allPermissions.categories || {}).map(([category, perms]) => {
                    const permIds = perms.map(p => p.id);
                    const selectedCount = permIds.filter(id => formData.permissions.includes(id)).length;
                    const allSelected = selectedCount === perms.length;
                    
                    return (
                      <AccordionItem key={category} value={category}>
                        <AccordionTrigger className="hover:no-underline">
                          <div className="flex items-center gap-3">
                            <Checkbox
                              checked={allSelected}
                              onClick={(e) => {
                                e.stopPropagation();
                                if (!(formData.isBuiltInView && !formData.customizing)) {
                                  toggleCategory(perms);
                                }
                              }}
                              disabled={formData.isBuiltInView && !formData.customizing && !formData.isBuiltInEdit}
                            />
                            <span className="capitalize">{category}</span>
                            <Badge variant="outline" className="text-xs">
                              {selectedCount}/{perms.length}
                            </Badge>
                          </div>
                        </AccordionTrigger>
                        <AccordionContent>
                          <div className="space-y-2 pl-8">
                            {perms.map((perm) => (
                              <label
                                key={perm.id}
                                className={`flex items-center gap-2 py-1 ${
                                  formData.isBuiltInView && !formData.customizing && !formData.isBuiltInEdit
                                    ? 'cursor-default opacity-80' 
                                    : 'cursor-pointer'
                                }`}
                              >
                                <Checkbox
                                  checked={formData.permissions.includes(perm.id)}
                                  onCheckedChange={() => togglePermission(perm.id)}
                                  disabled={formData.isBuiltInView && !formData.customizing && !formData.isBuiltInEdit}
                                />
                                <span className="text-sm">{perm.name}</span>
                              </label>
                            ))}
                          </div>
                        </AccordionContent>
                      </AccordionItem>
                    );
                  })}
                </Accordion>
              </ScrollArea>
            </div>

            <div className="flex justify-end gap-2 pt-4">
              <Button variant="outline" onClick={() => setDialogOpen(false)}>Cancel</Button>
              {formData.isBuiltInView && !formData.customizing ? (
                <Button 
                  onClick={() => setFormData(prev => ({ ...prev, customizing: true, isBuiltInView: false }))}
                  data-testid="customize-role-btn"
                >
                  <Plus className="w-4 h-4 mr-2" />
                  Create Custom Version
                </Button>
              ) : formData.isBuiltInEdit ? (
                <Button onClick={handleSaveBuiltInRole} disabled={saving} data-testid="save-builtin-role-btn">
                  {saving ? <LoadingSpinner size="sm" className="mr-2" /> : null}
                  Save Built-in Role
                </Button>
              ) : (
                <Button onClick={handleSave} disabled={saving} data-testid="save-role-btn">
                  {saving ? <LoadingSpinner size="sm" className="mr-2" /> : null}
                  {editingRole ? "Update Role" : "Create Role"}
                </Button>
              )}
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation */}
      <AlertDialog open={deleteDialog.open} onOpenChange={(open) => setDeleteDialog({ ...deleteDialog, open })}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Custom Role?</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete the &quot;{deleteDialog.role?.name}&quot; role?
              {deleteDialog.role?.member_count > 0 && (
                <span className="block mt-2 text-destructive">
                  Warning: {deleteDialog.role.member_count} member(s) currently have this role.
                  They will be assigned the default &quot;Team Member&quot; role.
                </span>
              )}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={handleDelete} disabled={deleting} className="bg-destructive text-destructive-foreground">
              {deleting ? <LoadingSpinner size="sm" /> : "Delete Role"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
