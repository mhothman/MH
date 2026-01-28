import { useState, useEffect } from "react";
import { useAuth } from "../context/AuthContext";
import {
  getOrganizations,
  getOrganizationMembers,
  getMyPermissions,
  hasPermission,
  Permission,
} from "../api";
import {
  getAutomations,
  createAutomation,
  updateAutomation,
  deleteAutomation,
  getAutomationHistory,
  getTriggerTypes,
  getActionTypes,
} from "../api/automations";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Textarea } from "../components/ui/textarea";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../components/ui/card";
import { Badge } from "../components/ui/badge";
import { Switch } from "../components/ui/switch";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "../components/ui/dialog";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "../components/ui/alert-dialog";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "../components/ui/sheet";
import { LoadingSpinner } from "../components/ui/loading-spinner";
import { toast } from "sonner";
import {
  Zap,
  Plus,
  Play,
  Pause,
  Trash2,
  Edit2,
  History,
  ArrowRight,
  CheckCircle,
  XCircle,
  Bell,
  Users,
  FileText,
  RefreshCw,
  Globe,
  Mail,
  AlertTriangle,
} from "lucide-react";

const TRIGGER_ICONS = {
  task_created: FileText,
  task_updated: RefreshCw,
  status_changed: ArrowRight,
  priority_changed: AlertTriangle,
  deadline_reached: History,
  task_assigned: Users,
  comment_added: FileText,
};

const ACTION_ICONS = {
  notify_users: Bell,
  assign_task: Users,
  update_task: RefreshCw,
  call_webhook: Globe,
  send_email: Mail,
};

export default function AutomationsPage() {
  const { user } = useAuth();
  const [loading, setLoading] = useState(true);
  const [organizations, setOrganizations] = useState([]);
  const [selectedOrg, setSelectedOrg] = useState(null);
  const [automations, setAutomations] = useState([]);
  const [triggerTypes, setTriggerTypes] = useState([]);
  const [actionTypes, setActionTypes] = useState([]);
  const [members, setMembers] = useState([]);
  const [permissions, setPermissions] = useState([]);
  
  // Permission check helper
  const canDo = (permission) => hasPermission(permissions, permission);
  
  // Dialog states
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [editingAutomation, setEditingAutomation] = useState(null);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [automationToDelete, setAutomationToDelete] = useState(null);
  const [historySheetOpen, setHistorySheetOpen] = useState(false);
  const [historyData, setHistoryData] = useState([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  
  // Form state
  const [formData, setFormData] = useState({
    name: "",
    description: "",
    triggerType: "",
    triggerConditions: {},
    actions: [{ type: "", config: {} }],
    enabled: true,
  });
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    loadInitialData();
  }, []);

  useEffect(() => {
    if (selectedOrg) {
      loadAutomations();
      loadMembers();
      loadPermissions();
    }
  }, [selectedOrg]);

  const loadPermissions = async () => {
    try {
      const data = await getMyPermissions(selectedOrg.org_id);
      setPermissions(data.permissions || []);
    } catch (e) {
      setPermissions([]);
    }
  };

  const loadInitialData = async () => {
    try {
      const [orgsData, triggers, actions] = await Promise.all([
        getOrganizations(),
        getTriggerTypes(),
        getActionTypes(),
      ]);
      setOrganizations(orgsData);
      setTriggerTypes(triggers.triggers || []);
      setActionTypes(actions.actions || []);
      if (orgsData.length > 0) {
        setSelectedOrg(orgsData[0]);
      }
    } catch (error) {
      toast.error("Failed to load data");
    } finally {
      setLoading(false);
    }
  };

  const loadAutomations = async () => {
    try {
      const data = await getAutomations(selectedOrg.org_id);
      setAutomations(data.automations || []);
    } catch (error) {
      if (error.message.includes("not available")) {
        setAutomations([]);
        toast.error("Automations feature not available on your plan");
      } else {
        toast.error("Failed to load automations");
      }
    }
  };

  const loadMembers = async () => {
    try {
      const data = await getOrganizationMembers(selectedOrg.org_id);
      setMembers(data);
    } catch (error) {
      console.error("Failed to load members:", error);
    }
  };

  const openCreateDialog = () => {
    setFormData({
      name: "",
      description: "",
      triggerType: "",
      triggerConditions: {},
      actions: [{ type: "", config: {} }],
      enabled: true,
    });
    setEditingAutomation(null);
    setCreateDialogOpen(true);
  };

  const openEditDialog = (automation) => {
    setFormData({
      name: automation.name,
      description: automation.description || "",
      triggerType: automation.trigger.type,
      triggerConditions: automation.trigger.conditions || {},
      actions: automation.actions.length > 0 ? automation.actions : [{ type: "", config: {} }],
      enabled: automation.enabled,
    });
    setEditingAutomation(automation);
    setCreateDialogOpen(true);
  };

  const handleSave = async () => {
    if (!formData.name || !formData.triggerType || !formData.actions[0]?.type) {
      toast.error("Please fill in all required fields");
      return;
    }

    setSaving(true);
    try {
      const payload = {
        name: formData.name,
        description: formData.description,
        trigger: {
          type: formData.triggerType,
          conditions: formData.triggerConditions,
        },
        actions: formData.actions.filter(a => a.type),
        enabled: formData.enabled,
      };

      if (editingAutomation) {
        await updateAutomation(editingAutomation.automation_id, payload);
        toast.success("Automation updated");
      } else {
        await createAutomation(selectedOrg.org_id, payload);
        toast.success("Automation created");
      }

      setCreateDialogOpen(false);
      loadAutomations();
    } catch (error) {
      toast.error(error.message || "Failed to save automation");
    } finally {
      setSaving(false);
    }
  };

  const handleToggleEnabled = async (automation) => {
    try {
      await updateAutomation(automation.automation_id, { enabled: !automation.enabled });
      toast.success(automation.enabled ? "Automation paused" : "Automation activated");
      loadAutomations();
    } catch (error) {
      toast.error("Failed to update automation");
    }
  };

  const handleDelete = async () => {
    if (!automationToDelete) return;
    try {
      await deleteAutomation(automationToDelete.automation_id);
      toast.success("Automation deleted");
      setDeleteDialogOpen(false);
      setAutomationToDelete(null);
      loadAutomations();
    } catch (error) {
      toast.error("Failed to delete automation");
    }
  };

  const openHistory = async (automation) => {
    setHistorySheetOpen(true);
    setHistoryLoading(true);
    try {
      const data = await getAutomationHistory(automation.automation_id);
      setHistoryData(data.history || []);
    } catch (error) {
      toast.error("Failed to load history");
    } finally {
      setHistoryLoading(false);
    }
  };

  const addAction = () => {
    setFormData(prev => ({
      ...prev,
      actions: [...prev.actions, { type: "", config: {} }],
    }));
  };

  const removeAction = (index) => {
    if (formData.actions.length <= 1) return;
    setFormData(prev => ({
      ...prev,
      actions: prev.actions.filter((_, i) => i !== index),
    }));
  };

  const updateAction = (index, field, value) => {
    setFormData(prev => ({
      ...prev,
      actions: prev.actions.map((action, i) => 
        i === index ? { ...action, [field]: value } : action
      ),
    }));
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-[60vh]">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="automations-page">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <Zap className="h-6 w-6 text-yellow-500" />
            Automations
          </h1>
          <p className="text-muted-foreground">
            Automate repetitive tasks with custom rules
          </p>
        </div>
        <div className="flex items-center gap-4">
          {organizations.length > 1 && (
            <Select value={selectedOrg?.org_id} onValueChange={(val) => setSelectedOrg(organizations.find(o => o.org_id === val))}>
              <SelectTrigger className="w-48">
                <SelectValue placeholder="Select organization" />
              </SelectTrigger>
              <SelectContent>
                {organizations.map((org) => (
                  <SelectItem key={org.org_id} value={org.org_id}>{org.name}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          )}
          {canDo(Permission.AUTOMATION_CREATE) && (
            <Button onClick={openCreateDialog} data-testid="create-automation-btn">
              <Plus className="h-4 w-4 mr-2" />
              New Automation
            </Button>
          )}
        </div>
      </div>

      {/* Automations List */}
      {automations.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <Zap className="h-12 w-12 text-muted-foreground mb-4" />
            <h3 className="text-lg font-medium mb-2">No automations yet</h3>
            <p className="text-muted-foreground text-center mb-4">
              Create your first automation to start saving time
            </p>
            {canDo(Permission.AUTOMATION_CREATE) && (
              <Button onClick={openCreateDialog}>
                <Plus className="h-4 w-4 mr-2" />
                Create Automation
              </Button>
            )}
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4">
          {automations.map((automation) => {
            const TriggerIcon = TRIGGER_ICONS[automation.trigger?.type] || Zap;
            return (
              <Card key={automation.automation_id} data-testid={`automation-${automation.automation_id}`}>
                <CardContent className="p-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4">
                      <div className={`p-2 rounded-lg ${automation.enabled ? 'bg-yellow-100 dark:bg-yellow-900/30' : 'bg-gray-100 dark:bg-gray-800'}`}>
                        <TriggerIcon className={`h-5 w-5 ${automation.enabled ? 'text-yellow-600' : 'text-gray-400'}`} />
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <h3 className="font-medium">{automation.name}</h3>
                          <Badge variant={automation.enabled ? "default" : "secondary"}>
                            {automation.enabled ? "Active" : "Paused"}
                          </Badge>
                        </div>
                        <p className="text-sm text-muted-foreground">{automation.description}</p>
                        <div className="flex items-center gap-4 mt-1 text-xs text-muted-foreground">
                          <span>Trigger: {automation.trigger?.type?.replace(/_/g, ' ')}</span>
                          <span>•</span>
                          <span>{automation.actions?.length || 0} action(s)</span>
                          <span>•</span>
                          <span>Run {automation.run_count || 0} times</span>
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <Button variant="ghost" size="icon" onClick={() => openHistory(automation)} title="View history">
                        <History className="h-4 w-4" />
                      </Button>
                      {canDo(Permission.AUTOMATION_EDIT) && (
                        <Button variant="ghost" size="icon" onClick={() => openEditDialog(automation)} title="Edit">
                          <Edit2 className="h-4 w-4" />
                        </Button>
                      )}
                      {canDo(Permission.AUTOMATION_EDIT) && (
                        <Button variant="ghost" size="icon" onClick={() => handleToggleEnabled(automation)} title={automation.enabled ? "Pause" : "Activate"}>
                          {automation.enabled ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}
                        </Button>
                      )}
                      {canDo(Permission.AUTOMATION_DELETE) && (
                        <Button variant="ghost" size="icon" onClick={() => { setAutomationToDelete(automation); setDeleteDialogOpen(true); }} className="text-destructive">
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      )}
                    </div>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}

      {/* Create/Edit Dialog */}
      <Dialog open={createDialogOpen} onOpenChange={setCreateDialogOpen}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{editingAutomation ? "Edit Automation" : "Create Automation"}</DialogTitle>
          </DialogHeader>
          <div className="space-y-6 py-4">
            {/* Name & Description */}
            <div className="space-y-4">
              <div>
                <Label htmlFor="name">Name *</Label>
                <Input
                  id="name"
                  value={formData.name}
                  onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
                  placeholder="e.g., Notify on task completion"
                  data-testid="automation-name-input"
                />
              </div>
              <div>
                <Label htmlFor="description">Description</Label>
                <Textarea
                  id="description"
                  value={formData.description}
                  onChange={(e) => setFormData(prev => ({ ...prev, description: e.target.value }))}
                  placeholder="What does this automation do?"
                  rows={2}
                />
              </div>
            </div>

            {/* Trigger */}
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-base">When (Trigger)</CardTitle>
                <CardDescription>What event should trigger this automation?</CardDescription>
              </CardHeader>
              <CardContent>
                <Select value={formData.triggerType} onValueChange={(val) => setFormData(prev => ({ ...prev, triggerType: val }))}>
                  <SelectTrigger data-testid="trigger-type-select">
                    <SelectValue placeholder="Select trigger type" />
                  </SelectTrigger>
                  <SelectContent>
                    {triggerTypes.map((trigger) => (
                      <SelectItem key={trigger.type} value={trigger.type}>
                        <div className="flex items-center gap-2">
                          {(() => { const Icon = TRIGGER_ICONS[trigger.type] || Zap; return <Icon className="h-4 w-4" />; })()}
                          <span>{trigger.name}</span>
                        </div>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                {formData.triggerType && (
                  <p className="text-xs text-muted-foreground mt-2">
                    {triggerTypes.find(t => t.type === formData.triggerType)?.description}
                  </p>
                )}

                {/* Condition inputs based on trigger type */}
                {formData.triggerType === "status_changed" && (
                  <div className="mt-4 grid grid-cols-2 gap-4">
                    <div>
                      <Label className="text-xs">From Status (optional)</Label>
                      <Input
                        placeholder="e.g., in_progress"
                        value={formData.triggerConditions.from_status || ""}
                        onChange={(e) => setFormData(prev => ({
                          ...prev,
                          triggerConditions: { ...prev.triggerConditions, from_status: e.target.value }
                        }))}
                      />
                    </div>
                    <div>
                      <Label className="text-xs">To Status (optional)</Label>
                      <Input
                        placeholder="e.g., done"
                        value={formData.triggerConditions.to_status || ""}
                        onChange={(e) => setFormData(prev => ({
                          ...prev,
                          triggerConditions: { ...prev.triggerConditions, to_status: e.target.value }
                        }))}
                      />
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Actions */}
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-base">Then (Actions)</CardTitle>
                <CardDescription>What should happen when the trigger fires?</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {formData.actions.map((action, index) => (
                  <div key={index} className="p-3 border rounded-lg space-y-3">
                    <div className="flex items-center justify-between">
                      <Label className="text-sm">Action {index + 1}</Label>
                      {formData.actions.length > 1 && (
                        <Button variant="ghost" size="sm" onClick={() => removeAction(index)}>
                          <Trash2 className="h-3 w-3" />
                        </Button>
                      )}
                    </div>
                    <Select value={action.type} onValueChange={(val) => updateAction(index, 'type', val)}>
                      <SelectTrigger data-testid={`action-type-select-${index}`}>
                        <SelectValue placeholder="Select action type" />
                      </SelectTrigger>
                      <SelectContent>
                        {actionTypes.map((at) => (
                          <SelectItem key={at.type} value={at.type}>
                            <div className="flex items-center gap-2">
                              {(() => { const Icon = ACTION_ICONS[at.type] || Zap; return <Icon className="h-4 w-4" />; })()}
                              <span>{at.name}</span>
                            </div>
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>

                    {/* Action-specific config */}
                    {action.type === "notify_users" && (
                      <div className="space-y-2">
                        <Label className="text-xs">Select users to notify</Label>
                        <Select
                          value={action.config.user_ids?.join(",") || ""}
                          onValueChange={(val) => updateAction(index, 'config', { ...action.config, user_ids: val.split(",").filter(Boolean) })}
                        >
                          <SelectTrigger>
                            <SelectValue placeholder="Select users" />
                          </SelectTrigger>
                          <SelectContent>
                            {members.map((m) => (
                              <SelectItem key={m.user_id} value={m.user_id}>{m.name}</SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                        <Input
                          placeholder="Notification title"
                          value={action.config.title || ""}
                          onChange={(e) => updateAction(index, 'config', { ...action.config, title: e.target.value })}
                        />
                        <Input
                          placeholder="Message (use {task_title}, {status} etc.)"
                          value={action.config.message || ""}
                          onChange={(e) => updateAction(index, 'config', { ...action.config, message: e.target.value })}
                        />
                      </div>
                    )}

                    {action.type === "assign_task" && (
                      <div className="space-y-2">
                        <Label className="text-xs">Assign to user</Label>
                        <Select
                          value={action.config.user_id || ""}
                          onValueChange={(val) => updateAction(index, 'config', { ...action.config, user_id: val })}
                        >
                          <SelectTrigger data-testid={`assign-user-select-${index}`}>
                            <SelectValue placeholder="Select user to assign" />
                          </SelectTrigger>
                          <SelectContent>
                            {members.map((m) => (
                              <SelectItem key={m.user_id} value={m.user_id}>
                                <div className="flex items-center gap-2">
                                  <Users className="h-3 w-3" />
                                  {m.name} ({m.email})
                                </div>
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>
                    )}

                    {action.type === "send_email" && (
                      <div className="space-y-2">
                        <Label className="text-xs">Send email to</Label>
                        <Select
                          value={action.config.user_id || ""}
                          onValueChange={(val) => updateAction(index, 'config', { ...action.config, user_id: val })}
                        >
                          <SelectTrigger data-testid={`email-user-select-${index}`}>
                            <SelectValue placeholder="Select recipient" />
                          </SelectTrigger>
                          <SelectContent>
                            {members.map((m) => (
                              <SelectItem key={m.user_id} value={m.user_id}>
                                <div className="flex items-center gap-2">
                                  <Mail className="h-3 w-3" />
                                  {m.name} ({m.email})
                                </div>
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                        <Input
                          placeholder="Email subject (use {task_title} etc.)"
                          value={action.config.subject || ""}
                          onChange={(e) => updateAction(index, 'config', { ...action.config, subject: e.target.value })}
                        />
                        <Textarea
                          placeholder="Email body (use {task_title}, {status}, {assignee} etc.)"
                          value={action.config.body || ""}
                          onChange={(e) => updateAction(index, 'config', { ...action.config, body: e.target.value })}
                          rows={3}
                        />
                      </div>
                    )}

                    {action.type === "call_webhook" && (
                      <div className="space-y-2">
                        <Input
                          placeholder="Webhook URL"
                          value={action.config.url || ""}
                          onChange={(e) => updateAction(index, 'config', { ...action.config, url: e.target.value })}
                        />
                        <Select
                          value={action.config.method || "POST"}
                          onValueChange={(val) => updateAction(index, 'config', { ...action.config, method: val })}
                        >
                          <SelectTrigger>
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="POST">POST</SelectItem>
                            <SelectItem value="GET">GET</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                    )}

                    {action.type === "update_task" && (
                      <div className="space-y-2">
                        <Label className="text-xs">Update fields</Label>
                        <div className="grid grid-cols-2 gap-2">
                          <Input
                            placeholder="Status"
                            value={action.config.fields?.status || ""}
                            onChange={(e) => updateAction(index, 'config', { ...action.config, fields: { ...action.config.fields, status: e.target.value } })}
                          />
                          <Input
                            placeholder="Priority"
                            value={action.config.fields?.priority || ""}
                            onChange={(e) => updateAction(index, 'config', { ...action.config, fields: { ...action.config.fields, priority: e.target.value } })}
                          />
                        </div>
                      </div>
                    )}
                  </div>
                ))}
                <Button variant="outline" size="sm" onClick={addAction}>
                  <Plus className="h-3 w-3 mr-1" />
                  Add Action
                </Button>
              </CardContent>
            </Card>

            {/* Enabled Toggle */}
            <div className="flex items-center justify-between p-3 border rounded-lg">
              <div>
                <Label>Enable automation</Label>
                <p className="text-xs text-muted-foreground">Start running this automation immediately</p>
              </div>
              <Switch
                checked={formData.enabled}
                onCheckedChange={(val) => setFormData(prev => ({ ...prev, enabled: val }))}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setCreateDialogOpen(false)}>Cancel</Button>
            <Button onClick={handleSave} disabled={saving} data-testid="save-automation-btn">
              {saving && <LoadingSpinner size="sm" className="mr-2" />}
              {editingAutomation ? "Update" : "Create"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation */}
      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete automation?</AlertDialogTitle>
            <AlertDialogDescription>
              This will permanently delete "{automationToDelete?.name}". This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={handleDelete} className="bg-destructive text-destructive-foreground">
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* History Sheet */}
      <Sheet open={historySheetOpen} onOpenChange={setHistorySheetOpen}>
        <SheetContent className="w-[500px] sm:max-w-[500px]">
          <SheetHeader>
            <SheetTitle>Execution History</SheetTitle>
          </SheetHeader>
          <div className="mt-4 space-y-3 max-h-[calc(100vh-120px)] overflow-y-auto">
            {historyLoading ? (
              <div className="flex justify-center py-8">
                <LoadingSpinner />
              </div>
            ) : historyData.length === 0 ? (
              <p className="text-center text-muted-foreground py-8">No execution history yet</p>
            ) : (
              historyData.map((run) => (
                <div key={run.run_id} className="p-3 border rounded-lg">
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      {run.success ? (
                        <CheckCircle className="h-4 w-4 text-green-500" />
                      ) : (
                        <XCircle className="h-4 w-4 text-red-500" />
                      )}
                      <span className="text-sm font-medium">{run.success ? "Success" : "Failed"}</span>
                    </div>
                    <span className="text-xs text-muted-foreground">
                      {new Date(run.executed_at).toLocaleString()}
                    </span>
                  </div>
                  <p className="text-xs text-muted-foreground">Duration: {run.duration_ms}ms</p>
                  {run.results?.length > 0 && (
                    <div className="mt-2 text-xs bg-muted p-2 rounded">
                      {run.results.map((r, i) => (
                        <div key={i}>{JSON.stringify(r)}</div>
                      ))}
                    </div>
                  )}
                </div>
              ))
            )}
          </div>
        </SheetContent>
      </Sheet>
    </div>
  );
}
