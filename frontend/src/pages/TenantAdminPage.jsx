import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Badge } from "../components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../components/ui/tabs";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "../components/ui/dialog";
import { Label } from "../components/ui/label";
import { Textarea } from "../components/ui/textarea";
import { Alert, AlertDescription, AlertTitle } from "../components/ui/alert";
import { LoadingSpinner } from "../components/ui/loading-spinner";
import { Shield, Building2, Users, Search, AlertTriangle, CheckCircle, Ban, PlayCircle, Info } from "lucide-react";
import { toast } from "sonner";
import { format } from "date-fns";

export default function TenantAdminPage() {
  const [organizations, setOrganizations] = useState([]);
  const [selectedOrg, setSelectedOrg] = useState(null);
  const [orgUsers, setOrgUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  const [activeTab, setActiveTab] = useState("organizations");
  const [suspendDialog, setSuspendDialog] = useState({ open: false, type: null, target: null });
  const [deleteDialog, setDeleteDialog] = useState({ open: false, type: null, target: null });
  const [reason, setReason] = useState("");
  const [processing, setProcessing] = useState(false);

  useEffect(() => {
    loadOrganizations();
  }, []);

  const loadOrganizations = async () => {
    setLoading(true);
    try {
      const API_URL = process.env.REACT_APP_BACKEND_URL;
      const token = localStorage.getItem('tenant_admin_token');
      
      const response = await fetch(`${API_URL}/api/tenant-admin/organizations`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      if (!response.ok) throw new Error('Failed to load organizations');
      
      const data = await response.json();
      setOrganizations(data);
    } catch (error) {
      toast.error(error.message || 'Failed to load organizations');
    } finally {
      setLoading(false);
    }
  };

  const loadOrgUsers = async (orgId) => {
    try {
      const API_URL = process.env.REACT_APP_BACKEND_URL;
      const token = localStorage.getItem('tenant_admin_token');
      
      const response = await fetch(`${API_URL}/api/tenant-admin/organizations/${orgId}/users`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      if (!response.ok) throw new Error('Failed to load users');
      
      const data = await response.json();
      setOrgUsers(data);
    } catch (error) {
      toast.error(error.message || 'Failed to load users');
    }
  };

  const handleSuspendOrg = async () => {
    if (!suspendDialog.target) return;

    setProcessing(true);
    try {
      const API_URL = process.env.REACT_APP_BACKEND_URL;
      const token = localStorage.getItem('tenant_admin_token');
      
      const response = await fetch(
        `${API_URL}/api/tenant-admin/organizations/${suspendDialog.target.org_id}/suspend`,
        {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({ reason })
        }
      );
      
      if (!response.ok) throw new Error('Failed to suspend organization');
      
      toast.success('Organization suspended successfully');
      setSuspendDialog({ open: false, type: null, target: null });
      setReason("");
      loadOrganizations();
    } catch (error) {
      toast.error(error.message || 'Failed to suspend organization');
    } finally {
      setProcessing(false);
    }
  };

  const handleActivateOrg = async (org) => {
    try {
      const API_URL = process.env.REACT_APP_BACKEND_URL;
      const token = localStorage.getItem('tenant_admin_token');
      
      const response = await fetch(
        `${API_URL}/api/tenant-admin/organizations/${org.org_id}/activate`,
        {
          method: 'POST',
          headers: { 'Authorization': `Bearer ${token}` }
        }
      );
      
      if (!response.ok) throw new Error('Failed to activate organization');
      
      toast.success('Organization activated successfully');
      loadOrganizations();
    } catch (error) {
      toast.error(error.message || 'Failed to activate organization');
    }
  };

  const handleSuspendUser = async () => {
    if (!suspendDialog.target) return;

    setProcessing(true);
    try {
      const API_URL = process.env.REACT_APP_BACKEND_URL;
      const token = localStorage.getItem('tenant_admin_token');
      
      const response = await fetch(
        `${API_URL}/api/tenant-admin/users/${suspendDialog.target.user_id}/suspend`,
        {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({ reason })
        }
      );
      
      if (!response.ok) throw new Error('Failed to suspend user');
      
      toast.success('User suspended successfully');
      setSuspendDialog({ open: false, type: null, target: null });
      setReason("");
      loadOrgUsers(selectedOrg.org_id);
    } catch (error) {
      toast.error(error.message || 'Failed to suspend user');
    } finally {
      setProcessing(false);
    }
  };

  const handleActivateUser = async (user) => {
    try {
      const API_URL = process.env.REACT_APP_BACKEND_URL;
      const token = localStorage.getItem('tenant_admin_token');
      
      const response = await fetch(
        `${API_URL}/api/tenant-admin/users/${user.user_id}/activate`,
        {
          method: 'POST',
          headers: { 'Authorization': `Bearer ${token}` }
        }
      );
      
      if (!response.ok) throw new Error('Failed to activate user');
      
      toast.success('User activated successfully');
      loadOrgUsers(selectedOrg.org_id);
    } catch (error) {
      toast.error(error.message || 'Failed to activate user');
    }
  };

  const handleDeleteOrg = async () => {
    if (!deleteDialog.target) return;

    setProcessing(true);
    try {
      const API_URL = process.env.REACT_APP_BACKEND_URL;
      const token = localStorage.getItem('tenant_admin_token');
      
      const response = await fetch(
        `${API_URL}/api/tenant-admin/organizations/${deleteDialog.target.org_id}`,
        {
          method: 'DELETE',
          headers: { 'Authorization': `Bearer ${token}` }
        }
      );
      
      if (!response.ok) throw new Error('Failed to delete organization');
      
      const result = await response.json();
      toast.success(result.message || 'Organization deleted successfully');
      setDeleteDialog({ open: false, type: null, target: null });
      loadOrganizations();
      if (selectedOrg?.org_id === deleteDialog.target.org_id) {
        setSelectedOrg(null);
        setOrgUsers([]);
        setActiveTab("organizations");
      }
    } catch (error) {
      toast.error(error.message || 'Failed to delete organization');
    } finally {
      setProcessing(false);
    }
  };

  const handleDeleteUser = async () => {
    if (!deleteDialog.target) return;

    setProcessing(true);
    try {
      const API_URL = process.env.REACT_APP_BACKEND_URL;
      const token = localStorage.getItem('tenant_admin_token');
      
      const response = await fetch(
        `${API_URL}/api/tenant-admin/users/${deleteDialog.target.user_id}`,
        {
          method: 'DELETE',
          headers: { 'Authorization': `Bearer ${token}` }
        }
      );
      
      if (!response.ok) throw new Error('Failed to delete user');
      
      toast.success('User deleted successfully');
      setDeleteDialog({ open: false, type: null, target: null });
      loadOrgUsers(selectedOrg.org_id);
    } catch (error) {
      toast.error(error.message || 'Failed to delete user');
    } finally {
      setProcessing(false);
    }
  };

  const filteredOrgs = organizations.filter(org =>
    org.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    org.org_id.toLowerCase().includes(searchTerm.toLowerCase())
  );

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background p-6">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex items-center gap-3">
          <Shield className="w-10 h-10 text-purple-600" />
          <div>
            <h1 className="font-heading text-3xl font-bold tracking-tight">
              Tenant Administration Portal
            </h1>
            <p className="text-muted-foreground mt-1">
              Manage all organizations and users across the tenant
            </p>
          </div>
        </div>

        {/* Warning Alert */}
        <Alert variant="default" className="border-purple-200 bg-purple-50 dark:bg-purple-950/20">
          <Info className="h-4 w-4 text-purple-600" />
          <AlertTitle className="text-purple-800 dark:text-purple-200">Tenant Admin Access</AlertTitle>
          <AlertDescription className="text-purple-700 dark:text-purple-300">
            You have tenant-level access. All actions are audited and logged. Use with caution.
          </AlertDescription>
        </Alert>

        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
          <TabsList className="grid w-full grid-cols-2">
            <TabsTrigger value="organizations">
              <Building2 className="w-4 h-4 mr-2" />
              Organizations ({organizations.length})
            </TabsTrigger>
            <TabsTrigger value="users" disabled={!selectedOrg}>
              <Users className="w-4 h-4 mr-2" />
              Users {selectedOrg ? `(${selectedOrg.name})` : ''}
            </TabsTrigger>
          </TabsList>

          {/* Organizations Tab */}
          <TabsContent value="organizations" className="space-y-4">
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle>All Organizations</CardTitle>
                  <div className="flex items-center gap-2">
                    <div className="relative">
                      <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
                      <Input
                        placeholder="Search organizations..."
                        value={searchTerm}
                        onChange={(e) => setSearchTerm(e.target.value)}
                        className="pl-8 w-64"
                      />
                    </div>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Organization</TableHead>
                      <TableHead>Owner</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead className="text-right">Members</TableHead>
                      <TableHead className="text-right">Projects</TableHead>
                      <TableHead className="text-right">Tasks</TableHead>
                      <TableHead>Created</TableHead>
                      <TableHead className="text-right">Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {filteredOrgs.map((org) => (
                      <TableRow key={org.org_id} className={org.status === 'suspended' ? 'bg-red-50 dark:bg-red-950/20' : ''}>
                        <TableCell>
                          <div>
                            <p className="font-medium">{org.name}</p>
                            <p className="text-xs text-muted-foreground">{org.org_id}</p>
                          </div>
                        </TableCell>
                        <TableCell>
                          <div>
                            <p className="text-sm">{org.owner_name}</p>
                            <p className="text-xs text-muted-foreground">{org.owner_email}</p>
                          </div>
                        </TableCell>
                        <TableCell>
                          <Badge variant={org.status === 'suspended' ? 'destructive' : 'default'}>
                            {org.status}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-right">{org.total_members}</TableCell>
                        <TableCell className="text-right">{org.total_projects}</TableCell>
                        <TableCell className="text-right">{org.total_tasks}</TableCell>
                        <TableCell className="text-sm">
                          {org.created_at ? format(new Date(org.created_at), 'MMM d, yyyy') : 'N/A'}
                        </TableCell>
                        <TableCell className="text-right">
                          <div className="flex gap-2 justify-end">
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => {
                                setSelectedOrg(org);
                                loadOrgUsers(org.org_id);
                                setActiveTab("users");
                              }}
                            >
                              View Users
                            </Button>
                            {org.status === 'active' ? (
                              <>
                                <Button
                                  size="sm"
                                  variant="destructive"
                                  onClick={() => setSuspendDialog({ open: true, type: 'org', target: org })}
                                >
                                  <Ban className="w-4 h-4 mr-1" />
                                  Suspend
                                </Button>
                                <Button
                                  size="sm"
                                  variant="destructive"
                                  onClick={() => setDeleteDialog({ open: true, type: 'org', target: org })}
                                >
                                  Delete
                                </Button>
                              </>
                            ) : (
                              <>
                                <Button
                                  size="sm"
                                  variant="default"
                                  onClick={() => handleActivateOrg(org)}
                                >
                                  <PlayCircle className="w-4 h-4 mr-1" />
                                  Activate
                                </Button>
                                <Button
                                  size="sm"
                                  variant="destructive"
                                  onClick={() => setDeleteDialog({ open: true, type: 'org', target: org })}
                                >
                                  Delete
                                </Button>
                              </>
                            )}
                          </div>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
                {filteredOrgs.length === 0 && (
                  <div className="text-center py-8 text-muted-foreground">
                    No organizations found
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          {/* Users Tab */}
          <TabsContent value="users" className="space-y-4">
            {selectedOrg && (
              <Card>
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <div>
                      <CardTitle>Users in {selectedOrg.name}</CardTitle>
                      <CardDescription>{orgUsers.length} members</CardDescription>
                    </div>
                    {selectedOrg.status === 'suspended' && (
                      <Badge variant="destructive">Organization Suspended</Badge>
                    )}
                  </div>
                </CardHeader>
                <CardContent>
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>User</TableHead>
                        <TableHead>Role</TableHead>
                        <TableHead>Status</TableHead>
                        <TableHead>Last Login</TableHead>
                        <TableHead>Created</TableHead>
                        <TableHead className="text-right">Actions</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {orgUsers.map((user) => (
                        <TableRow key={user.user_id} className={user.status === 'suspended' ? 'bg-red-50 dark:bg-red-950/20' : ''}>
                          <TableCell>
                            <div>
                              <p className="font-medium">{user.name}</p>
                              <p className="text-xs text-muted-foreground">{user.email}</p>
                            </div>
                          </TableCell>
                          <TableCell>
                            <Badge variant="outline">{user.role.replace('_', ' ')}</Badge>
                          </TableCell>
                          <TableCell>
                            <Badge variant={user.status === 'suspended' ? 'destructive' : 'secondary'}>
                              {user.status}
                            </Badge>
                          </TableCell>
                          <TableCell className="text-sm">
                            {user.last_login ? format(new Date(user.last_login), 'MMM d, HH:mm') : 'Never'}
                          </TableCell>
                          <TableCell className="text-sm">
                            {user.created_at ? format(new Date(user.created_at), 'MMM d, yyyy') : 'N/A'}
                          </TableCell>
                          <TableCell className="text-right">
                            {user.status === 'active' ? (
                              <>
                                <Button
                                  size="sm"
                                  variant="destructive"
                                  onClick={() => setSuspendDialog({ open: true, type: 'user', target: user })}
                                >
                                  <Ban className="w-4 h-4 mr-1" />
                                  Suspend
                                </Button>
                                <Button
                                  size="sm"
                                  variant="destructive"
                                  onClick={() => setDeleteDialog({ open: true, type: 'user', target: user })}
                                  className="ml-2"
                                >
                                  Delete
                                </Button>
                              </>
                            ) : (
                              <>
                                <Button
                                  size="sm"
                                  variant="default"
                                  onClick={() => handleActivateUser(user)}
                                >
                                  <PlayCircle className="w-4 h-4 mr-1" />
                                  Activate
                                </Button>
                                <Button
                                  size="sm"
                                  variant="destructive"
                                  onClick={() => setDeleteDialog({ open: true, type: 'user', target: user })}
                                  className="ml-2"
                                >
                                  Delete
                                </Button>
                              </>
                            )}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                  {orgUsers.length === 0 && (
                    <div className="text-center py-8 text-muted-foreground">
                      No users in this organization
                    </div>
                  )}
                </CardContent>
              </Card>
            )}
          </TabsContent>
        </Tabs>

        {/* Suspend/Activate Confirmation Dialog */}
        <Dialog open={suspendDialog.open} onOpenChange={(open) => !processing && setSuspendDialog({ ...suspendDialog, open })}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                <AlertTriangle className="w-5 h-5 text-red-600" />
                Confirm {suspendDialog.type === 'org' ? 'Organization' : 'User'} Suspension
              </DialogTitle>
              <DialogDescription>
                {suspendDialog.type === 'org' ? (
                  <>
                    Suspending <strong>{suspendDialog.target?.name}</strong> will:
                    <ul className="list-disc list-inside mt-2 space-y-1">
                      <li>Block all user logins</li>
                      <li>Prevent any data modifications</li>
                      <li>Place organization in read-only mode</li>
                    </ul>
                  </>
                ) : (
                  <>
                    Suspending <strong>{suspendDialog.target?.name}</strong> ({suspendDialog.target?.email}) will:
                    <ul className="list-disc list-inside mt-2 space-y-1">
                      <li>Block user login</li>
                      <li>Force logout if currently active</li>
                      <li>Revoke all access permissions</li>
                    </ul>
                  </>
                )}
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <Label htmlFor="reason">Reason for Suspension *</Label>
                <Textarea
                  id="reason"
                  placeholder="Explain why this action is necessary..."
                  value={reason}
                  onChange={(e) => setReason(e.target.value)}
                  rows={3}
                  required
                />
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setSuspendDialog({ open: false, type: null, target: null })} disabled={processing}>
                Cancel
              </Button>
              <Button
                variant="destructive"
                onClick={suspendDialog.type === 'org' ? handleSuspendOrg : handleSuspendUser}
                disabled={processing || !reason.trim()}
              >
                {processing ? <LoadingSpinner size="sm" className="mr-2" /> : <Ban className="w-4 h-4 mr-2" />}
                Suspend {suspendDialog.type === 'org' ? 'Organization' : 'User'}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        {/* Delete Confirmation Dialog */}
        <Dialog open={deleteDialog.open} onOpenChange={(open) => !processing && setDeleteDialog({ ...deleteDialog, open })}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2 text-red-600">
                <AlertTriangle className="w-5 h-5" />
                Permanently Delete {deleteDialog.type === 'org' ? 'Organization' : 'User'}?
              </DialogTitle>
              <DialogDescription>
                {deleteDialog.type === 'org' ? (
                  <>
                    <p className="font-semibold text-red-600 mb-2">⚠️ WARNING: This action CANNOT be undone!</p>
                    <p>Deleting <strong>{deleteDialog.target?.name}</strong> will permanently remove:</p>
                    <ul className="list-disc list-inside mt-2 space-y-1 text-red-700">
                      <li>All projects ({deleteDialog.target?.total_projects || 0})</li>
                      <li>All tasks ({deleteDialog.target?.total_tasks || 0})</li>
                      <li>All members ({deleteDialog.target?.total_members || 0})</li>
                      <li>All time entries, budgets, documents</li>
                      <li>Complete organization data</li>
                    </ul>
                  </>
                ) : (
                  <>
                    <p className="font-semibold text-red-600 mb-2">⚠️ WARNING: This action CANNOT be undone!</p>
                    <p>Deleting <strong>{deleteDialog.target?.name}</strong> ({deleteDialog.target?.email}) will:</p>
                    <ul className="list-disc list-inside mt-2 space-y-1 text-red-700">
                      <li>Remove user from organization</li>
                      <li>Delete all user's time entries</li>
                      <li>Remove user's comments and data</li>
                      <li>Cannot be recovered</li>
                    </ul>
                  </>
                )}
              </DialogDescription>
            </DialogHeader>
            <div className="bg-red-50 dark:bg-red-950/30 border-2 border-red-200 dark:border-red-800 rounded-lg p-4">
              <p className="text-sm font-medium text-red-800 dark:text-red-200">
                Type "{deleteDialog.type === 'org' ? deleteDialog.target?.name : deleteDialog.target?.email}" to confirm deletion:
              </p>
              <Input
                className="mt-2"
                placeholder={deleteDialog.type === 'org' ? deleteDialog.target?.name : deleteDialog.target?.email}
                value={reason}
                onChange={(e) => setReason(e.target.value)}
              />
            </div>
            <DialogFooter>
              <Button 
                variant="outline" 
                onClick={() => { 
                  setDeleteDialog({ open: false, type: null, target: null }); 
                  setReason(""); 
                }} 
                disabled={processing}
              >
                Cancel
              </Button>
              <Button
                variant="destructive"
                onClick={deleteDialog.type === 'org' ? handleDeleteOrg : handleDeleteUser}
                disabled={
                  processing || 
                  reason !== (deleteDialog.type === 'org' ? deleteDialog.target?.name : deleteDialog.target?.email)
                }
              >
                {processing ? <LoadingSpinner size="sm" className="mr-2" /> : null}
                Permanently Delete
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    </div>
  );
}
