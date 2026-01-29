/**
 * DocumentWorkflowSettings - Organization-level document approval workflow configuration
 * Location: System Settings → Documents Tab
 */
import { useState, useEffect } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../ui/card";
import { Button } from "../ui/button";
import { Input } from "../ui/input";
import { Label } from "../ui/label";
import { Badge } from "../ui/badge";
import { Switch } from "../ui/switch";
import { Textarea } from "../ui/textarea";
import { Checkbox } from "../ui/checkbox";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../ui/select";
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
import { LoadingSpinner } from "../ui/loading-spinner";
import { toast } from "sonner";
import {
  Plus,
  Pencil,
  Trash2,
  FileText,
  ArrowRight,
  Clock,
  Users,
  Globe,
  FolderOpen,
  Settings2,
  AlertTriangle,
  CheckCircle2,
} from "lucide-react";
import {
  getDocumentWorkflows,
  getDocumentWorkflow,
  createDocumentWorkflow,
  updateDocumentWorkflow,
  deleteDocumentWorkflow,
  createDocumentWorkflowRule,
  updateDocumentWorkflowRule,
  deleteDocumentWorkflowRule,
  getStatusColor,
  getStatusLabel,
} from "../../api/documents";
import { getProjects } from "../../api/projects";

const APPROVAL_TYPES = [
  { value: "single", label: "Single Approval", description: "Any one approver can approve" },
  { value: "multi", label: "Multi Approval", description: "All approvers must approve" },
  { value: "sequential", label: "Sequential", description: "Approvers approve in order" },
];

const APPROVER_ROLES = [
  { value: "org_admin", label: "Organization Admin" },
  { value: "project_manager", label: "Project Manager" },
  { value: "document_owner", label: "Document Owner" },
  { value: "legal", label: "Legal Team" },
  { value: "compliance", label: "Compliance Team" },
  { value: "department_head", label: "Department Head" },
];

const SCOPE_OPTIONS = [
  { value: "global", label: "Global", icon: Globe, description: "Applies to ALL documents" },
  { value: "selective", label: "Selective", icon: FolderOpen, description: "Filter by project or type" },
];

const DOCUMENT_TYPES = [
  { value: "policy", label: "Policy" },
  { value: "procedure", label: "Procedure" },
  { value: "specification", label: "Specification" },
  { value: "contract", label: "Contract" },
  { value: "report", label: "Report" },
  { value: "proposal", label: "Proposal" },
  { value: "template", label: "Template" },
  { value: "other", label: "Other" },
];

const DOCUMENT_STATUSES = [
  { value: "draft", label: "Draft", color: "#6b7280" },
  { value: "in_review", label: "In Review", color: "#f59e0b" },
  { value: "pending_approval", label: "Pending Approval", color: "#8b5cf6" },
  { value: "approved", label: "Approved", color: "#22c55e" },
  { value: "published", label: "Published", color: "#3b82f6" },
  { value: "archived", label: "Archived", color: "#9ca3af" },
  { value: "rejected", label: "Rejected", color: "#ef4444" },
];

// Common rule presets for quick setup
const RULE_PRESETS = [
  { 
    name: "Submit for Review", 
    from_status: "draft", 
    to_status: "in_review",
    description: "Require approval to submit for review"
  },
  { 
    name: "Approve Document", 
    from_status: "in_review", 
    to_status: "approved",
    description: "Require approval after review"
  },
  { 
    name: "Publish Document", 
    from_status: "approved", 
    to_status: "published",
    description: "Require approval to publish"
  },
  { 
    name: "Direct Publish", 
    from_status: "draft", 
    to_status: "published",
    description: "Require approval for direct publishing"
  },
  { 
    name: "Archive Document", 
    from_status: "published", 
    to_status: "archived",
    description: "Require approval to archive"
  },
  { 
    name: "Reopen Draft", 
    from_status: "rejected", 
    to_status: "draft",
    description: "Require approval to reopen rejected documents"
  },
];

export function DocumentWorkflowSettings({ orgId, canManageWorkflows = false }) {
  const [workflows, setWorkflows] = useState([]);
  const [selectedWorkflow, setSelectedWorkflow] = useState(null);
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [workflowDialogOpen, setWorkflowDialogOpen] = useState(false);
  const [ruleDialogOpen, setRuleDialogOpen] = useState(false);
  const [editingWorkflow, setEditingWorkflow] = useState(null);
  const [editingRule, setEditingRule] = useState(null);
  const [deleteDialog, setDeleteDialog] = useState({ open: false, type: null, item: null });
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);

  const [workflowForm, setWorkflowForm] = useState({ 
    name: "", 
    description: "", 
    scope: "selective",
    active: true,
    document_types: [],
    project_ids: [],
  });
  
  const [ruleForm, setRuleForm] = useState({
    from_status: "",
    to_status: "",
    description: "",
    approval_required: true,
    approval_type: "single",
    approver_role: "org_admin",
    approval_timeout_minutes: null,
    auto_approve_on_timeout: false,
    notify_on_request: true,
    notify_on_resolution: true,
    pause_sla: true,
  });

  useEffect(() => {
    if (orgId) {
      loadData();
    }
  }, [orgId]);

  const loadData = async () => {
    try {
      setLoading(true);
      // Load workflows and projects in parallel
      const [workflowsData, projectsData] = await Promise.all([
        getDocumentWorkflows(orgId),
        getProjects()
      ]);
      setWorkflows(workflowsData);
      setProjects(projectsData.filter(p => p.org_id === orgId));
      
      // Auto-select the first workflow if any (already includes rules)
      if (workflowsData.length > 0) {
        setSelectedWorkflow(workflowsData[0]);
      }
    } catch (error) {
      toast.error("Failed to load document workflows");
    } finally {
      setLoading(false);
    }
  };
      
      // Auto-select the first workflow if any
      if (workflowsData.length > 0) {
        const fullWorkflow = await getDocumentWorkflow(workflowsData[0].workflow_id);
        setSelectedWorkflow(fullWorkflow);
      }
    } catch (error) {
      toast.error("Failed to load document workflows");
    } finally {
      setLoading(false);
    }
  };

  const selectWorkflow = async (workflowId) => {
    try {
      const fullWorkflow = await getDocumentWorkflow(workflowId);
      setSelectedWorkflow(fullWorkflow);
    } catch (error) {
      toast.error("Failed to load workflow details");
    }
  };

  // Workflow CRUD handlers
  const openCreateWorkflowDialog = () => {
    const hasGlobal = workflows.some(w => w.scope === "global" && w.active);
    
    setEditingWorkflow(null);
    setWorkflowForm({ 
      name: "", 
      description: "", 
      scope: hasGlobal ? "selective" : "global",
      active: true,
      document_types: [],
      project_ids: [],
    });
    setWorkflowDialogOpen(true);
  };

  const openEditWorkflowDialog = (workflow) => {
    setEditingWorkflow(workflow);
    setWorkflowForm({
      name: workflow.name,
      description: workflow.description || "",
      scope: workflow.scope || "selective",
      active: workflow.active,
      document_types: workflow.document_types || [],
      project_ids: workflow.project_ids || [],
    });
    setWorkflowDialogOpen(true);
  };

  const handleSaveWorkflow = async () => {
    if (!workflowForm.name.trim()) {
      toast.error("Please enter a workflow name");
      return;
    }

    setSaving(true);
    try {
      if (editingWorkflow) {
        await updateDocumentWorkflow(editingWorkflow.workflow_id, workflowForm);
        toast.success("Workflow updated successfully");
      } else {
        await createDocumentWorkflow(orgId, workflowForm);
        toast.success("Workflow created successfully");
      }
      setWorkflowDialogOpen(false);
      loadData();
    } catch (error) {
      toast.error(error.message || "Failed to save workflow");
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteWorkflow = async () => {
    if (!deleteDialog.item) return;
    
    setDeleting(true);
    try {
      await deleteDocumentWorkflow(deleteDialog.item.workflow_id);
      toast.success("Workflow deleted successfully");
      setDeleteDialog({ open: false, type: null, item: null });
      if (selectedWorkflow?.workflow_id === deleteDialog.item.workflow_id) {
        setSelectedWorkflow(null);
      }
      loadData();
    } catch (error) {
      toast.error(error.message || "Failed to delete workflow");
    } finally {
      setDeleting(false);
    }
  };

  // Rule CRUD handlers
  const openCreateRuleDialog = () => {
    setEditingRule(null);
    setRuleForm({
      from_status: "",
      to_status: "",
      description: "",
      approval_required: true,
      approval_type: "single",
      approver_role: "org_admin",
      approval_timeout_minutes: null,
      auto_approve_on_timeout: false,
      notify_on_request: true,
      notify_on_resolution: true,
      pause_sla: true,
    });
    setRuleDialogOpen(true);
  };

  const openEditRuleDialog = (rule) => {
    setEditingRule(rule);
    setRuleForm({
      from_status: rule.from_status,
      to_status: rule.to_status,
      description: rule.description || "",
      approval_required: rule.approval_required,
      approval_type: rule.approval_type,
      approver_role: rule.approver_role,
      approval_timeout_minutes: rule.approval_timeout_minutes,
      auto_approve_on_timeout: rule.auto_approve_on_timeout,
      notify_on_request: rule.notify_on_request ?? true,
      notify_on_resolution: rule.notify_on_resolution ?? true,
      pause_sla: rule.pause_sla ?? true,
    });
    setRuleDialogOpen(true);
  };

  const handleSaveRule = async () => {
    if (!ruleForm.from_status || !ruleForm.to_status) {
      toast.error("Please select both source and target status");
      return;
    }
    if (ruleForm.from_status === ruleForm.to_status) {
      toast.error("Source and target status must be different");
      return;
    }

    setSaving(true);
    try {
      if (editingRule) {
        await updateDocumentWorkflowRule(editingRule.rule_id, ruleForm);
        toast.success("Rule updated successfully");
      } else {
        await createDocumentWorkflowRule(selectedWorkflow.workflow_id, ruleForm);
        toast.success("Rule created successfully");
      }
      setRuleDialogOpen(false);
      selectWorkflow(selectedWorkflow.workflow_id);
    } catch (error) {
      toast.error(error.message || "Failed to save rule");
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteRule = async () => {
    if (!deleteDialog.item) return;
    
    setDeleting(true);
    try {
      await deleteDocumentWorkflowRule(deleteDialog.item.rule_id);
      toast.success("Rule deleted successfully");
      setDeleteDialog({ open: false, type: null, item: null });
      selectWorkflow(selectedWorkflow.workflow_id);
    } catch (error) {
      toast.error(error.message || "Failed to delete rule");
    } finally {
      setDeleting(false);
    }
  };

  const toggleDocumentType = (typeValue) => {
    setWorkflowForm(prev => ({
      ...prev,
      document_types: prev.document_types.includes(typeValue)
        ? prev.document_types.filter(t => t !== typeValue)
        : [...prev.document_types, typeValue]
    }));
  };

  const toggleProject = (projectId) => {
    setWorkflowForm(prev => ({
      ...prev,
      project_ids: prev.project_ids.includes(projectId)
        ? prev.project_ids.filter(id => id !== projectId)
        : [...prev.project_ids, projectId]
    }));
  };

  const hasGlobalWorkflow = workflows.some(w => w.scope === "global" && w.active);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <LoadingSpinner />
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="document-workflow-settings">
      {/* Workflows List */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <FileText className="w-5 h-5" />
              Document Approval Workflows
            </CardTitle>
            <CardDescription>
              Configure approval workflows for document status transitions
            </CardDescription>
          </div>
          {canManageWorkflows && (
            <Button onClick={openCreateWorkflowDialog} data-testid="create-doc-workflow-btn">
              <Plus className="w-4 h-4 mr-2" />
              Create Workflow
            </Button>
          )}
        </CardHeader>
        <CardContent>
          {workflows.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              <FileText className="w-12 h-12 mx-auto mb-3 opacity-50" />
              <p>No document workflows configured</p>
              {canManageWorkflows && (
                <p className="text-sm mt-1">Create a workflow to require approvals for document status changes</p>
              )}
            </div>
          ) : (
            <div className="space-y-3">
              {workflows.map((workflow) => (
                <div
                  key={workflow.workflow_id}
                  className={`flex items-center justify-between p-4 border rounded-lg cursor-pointer transition-colors ${
                    selectedWorkflow?.workflow_id === workflow.workflow_id
                      ? "border-primary bg-primary/5"
                      : "hover:border-muted-foreground/30"
                  }`}
                  onClick={() => selectWorkflow(workflow.workflow_id)}
                  data-testid={`doc-workflow-item-${workflow.workflow_id}`}
                >
                  <div className="flex items-center gap-3">
                    <div className={`w-2 h-2 rounded-full ${workflow.active ? "bg-green-500" : "bg-gray-400"}`} />
                    <div>
                      <div className="flex items-center gap-2">
                        <p className="font-medium">{workflow.name}</p>
                        <Badge variant={workflow.scope === "global" ? "default" : "secondary"} className="text-xs">
                          {workflow.scope === "global" ? (
                            <><Globe className="w-3 h-3 mr-1" />Global</>
                          ) : (
                            <><FolderOpen className="w-3 h-3 mr-1" />Selective</>
                          )}
                        </Badge>
                      </div>
                      <p className="text-sm text-muted-foreground">
                        {workflow.rules_count} rule{workflow.rules_count !== 1 ? "s" : ""}
                        {!workflow.active && " • Inactive"}
                      </p>
                    </div>
                  </div>
                  {canManageWorkflows && (
                    <div className="flex items-center gap-1" onClick={(e) => e.stopPropagation()}>
                      <Button variant="ghost" size="sm" onClick={() => openEditWorkflowDialog(workflow)}>
                        <Pencil className="w-4 h-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        className="text-destructive"
                        onClick={() => setDeleteDialog({ open: true, type: "workflow", item: workflow })}
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

      {/* Selected Workflow Details */}
      {selectedWorkflow && (
        <>
          {/* Scope Info Card */}
          {selectedWorkflow.scope === "global" && (
            <Card className="border-amber-200 bg-amber-50/50 dark:bg-amber-950/20 dark:border-amber-800">
              <CardContent className="flex items-center gap-3 pt-4">
                <Globe className="w-5 h-5 text-amber-600" />
                <p className="text-sm text-amber-800 dark:text-amber-200">
                  This is a <strong>global workflow</strong> - it automatically applies to all documents in the organization.
                </p>
              </CardContent>
            </Card>
          )}

          {selectedWorkflow.scope === "selective" && (
            <Card>
              <CardContent className="pt-4">
                <div className="space-y-4">
                  {selectedWorkflow.document_types?.length > 0 && (
                    <div>
                      <p className="text-sm font-medium mb-2">Applies to document types:</p>
                      <div className="flex flex-wrap gap-2">
                        {selectedWorkflow.document_types.map(type => (
                          <Badge key={type} variant="outline">{type.replace("_", " ").toUpperCase()}</Badge>
                        ))}
                      </div>
                    </div>
                  )}
                  {selectedWorkflow.project_ids?.length > 0 && (
                    <div>
                      <p className="text-sm font-medium mb-2">Applies to projects:</p>
                      <div className="flex flex-wrap gap-2">
                        {selectedWorkflow.project_ids.map(projectId => {
                          const project = projects.find(p => p.project_id === projectId);
                          return (
                            <Badge key={projectId} variant="outline">
                              {project?.name || projectId}
                            </Badge>
                          );
                        })}
                      </div>
                    </div>
                  )}
                  {(!selectedWorkflow.document_types?.length && !selectedWorkflow.project_ids?.length) && (
                    <p className="text-sm text-muted-foreground">
                      No filters configured. This workflow applies to all documents.
                    </p>
                  )}
                </div>
              </CardContent>
            </Card>
          )}

          {/* Workflow Rules */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle className="flex items-center gap-2">
                  <Settings2 className="w-5 h-5" />
                  Approval Rules: {selectedWorkflow.name}
                </CardTitle>
                <CardDescription>
                  Configure which document status transitions require approval
                </CardDescription>
              </div>
              {canManageWorkflows && (
                <Button onClick={openCreateRuleDialog} data-testid="create-doc-rule-btn">
                  <Plus className="w-4 h-4 mr-2" />
                  Add Rule
                </Button>
              )}
            </CardHeader>
            <CardContent>
              {/* Quick Add Presets */}
              {canManageWorkflows && (!selectedWorkflow.rules || selectedWorkflow.rules.length < 6) && (
                <div className="mb-6 p-4 border border-dashed rounded-lg bg-muted/30">
                  <p className="text-sm font-medium mb-3 flex items-center gap-2">
                    <CheckCircle2 className="w-4 h-4 text-green-500" />
                    Quick Add Common Rules
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {RULE_PRESETS
                      .filter(preset => 
                        !selectedWorkflow.rules?.some(r => 
                          r.from_status === preset.from_status && r.to_status === preset.to_status
                        )
                      )
                      .map((preset) => (
                        <Button
                          key={`${preset.from_status}-${preset.to_status}`}
                          variant="outline"
                          size="sm"
                          onClick={() => {
                            setEditingRule(null);
                            setRuleForm({
                              from_status: preset.from_status,
                              to_status: preset.to_status,
                              description: preset.description,
                              approval_required: true,
                              approval_type: "single",
                              approver_role: "org_admin",
                              approval_timeout_minutes: null,
                              auto_approve_on_timeout: false,
                              notify_on_request: true,
                              notify_on_resolution: true,
                              pause_sla: true,
                            });
                            setRuleDialogOpen(true);
                          }}
                          title={preset.description}
                        >
                          <Plus className="w-3 h-3 mr-1" />
                          {preset.name}
                        </Button>
                      ))}
                  </div>
                </div>
              )}

              {(!selectedWorkflow.rules || selectedWorkflow.rules.length === 0) ? (
                <div className="text-center py-8 text-muted-foreground">
                  <AlertTriangle className="w-12 h-12 mx-auto mb-3 opacity-50" />
                  <p>No approval rules defined</p>
                  {canManageWorkflows && (
                    <p className="text-sm mt-1">Use the presets above or add a custom rule</p>
                  )}
                </div>
              ) : (
                <div className="space-y-3">
                  {selectedWorkflow.rules.map((rule) => (
                    <div
                      key={rule.rule_id}
                      className="flex items-center justify-between p-4 border rounded-lg"
                      data-testid={`doc-rule-item-${rule.rule_id}`}
                    >
                      <div className="flex-1">
                        <div className="flex items-center gap-4">
                          {/* Status Transition */}
                          <div className="flex items-center gap-2">
                            <Badge
                              variant="outline"
                              style={{ borderColor: getStatusColor(rule.from_status), color: getStatusColor(rule.from_status) }}
                            >
                              {getStatusLabel(rule.from_status)}
                            </Badge>
                            <ArrowRight className="w-4 h-4 text-muted-foreground" />
                            <Badge
                              variant="outline"
                              style={{ borderColor: getStatusColor(rule.to_status), color: getStatusColor(rule.to_status) }}
                            >
                              {getStatusLabel(rule.to_status)}
                            </Badge>
                          </div>
                          
                          {/* Rule Info */}
                          <div className="flex items-center gap-2 text-sm text-muted-foreground">
                            <Users className="w-4 h-4" />
                            <span className="capitalize">{rule.approver_role.replace(/_/g, " ")}</span>
                            <span className="text-xs">
                              ({rule.approval_type === "single" ? "Any one" : rule.approval_type === "multi" ? "All" : "Sequential"})
                            </span>
                          </div>
                          
                          {rule.approval_timeout_minutes && (
                            <div className="flex items-center gap-1 text-sm text-muted-foreground">
                              <Clock className="w-4 h-4" />
                              <span>{rule.approval_timeout_minutes}m</span>
                              {rule.auto_approve_on_timeout && (
                                <Badge variant="secondary" className="text-xs">Auto-approve</Badge>
                              )}
                            </div>
                          )}
                        </div>
                        {rule.description && (
                          <p className="text-sm text-muted-foreground mt-2 pl-1">{rule.description}</p>
                        )}
                      </div>

                      {canManageWorkflows && (
                        <div className="flex items-center gap-1">
                          <Button variant="ghost" size="sm" onClick={() => openEditRuleDialog(rule)}>
                            <Pencil className="w-4 h-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            className="text-destructive"
                            onClick={() => setDeleteDialog({ open: true, type: "rule", item: rule })}
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
        </>
      )}

      {/* Create/Edit Workflow Dialog */}
      <Dialog open={workflowDialogOpen} onOpenChange={setWorkflowDialogOpen}>
        <DialogContent className="max-w-lg max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{editingWorkflow ? "Edit Document Workflow" : "Create Document Workflow"}</DialogTitle>
            <DialogDescription>
              Configure the document approval workflow settings
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 pt-4">
            <div className="space-y-2">
              <Label htmlFor="doc-workflow-name">Workflow Name</Label>
              <Input
                id="doc-workflow-name"
                placeholder="e.g., Contract Approval Workflow"
                value={workflowForm.name}
                onChange={(e) => setWorkflowForm(prev => ({ ...prev, name: e.target.value }))}
                data-testid="doc-workflow-name-input"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="doc-workflow-description">Description</Label>
              <Textarea
                id="doc-workflow-description"
                placeholder="Describe when this workflow should be used"
                value={workflowForm.description}
                onChange={(e) => setWorkflowForm(prev => ({ ...prev, description: e.target.value }))}
                rows={2}
              />
            </div>

            <div className="space-y-2">
              <Label>Scope</Label>
              <div className="grid grid-cols-2 gap-3">
                {SCOPE_OPTIONS.map((option) => {
                  const isGlobal = option.value === "global";
                  const isDisabled = isGlobal && hasGlobalWorkflow && editingWorkflow?.scope !== "global";
                  const Icon = option.icon;
                  
                  return (
                    <div
                      key={option.value}
                      className={`border rounded-lg p-3 cursor-pointer transition-colors ${
                        workflowForm.scope === option.value
                          ? "border-primary bg-primary/5"
                          : "hover:border-muted-foreground/30"
                      } ${isDisabled ? "opacity-50 cursor-not-allowed" : ""}`}
                      onClick={() => !isDisabled && setWorkflowForm(prev => ({ ...prev, scope: option.value }))}
                    >
                      <div className="flex items-center gap-2">
                        <Icon className="w-4 h-4" />
                        <span className="font-medium">{option.label}</span>
                      </div>
                      <p className="text-xs text-muted-foreground mt-1">{option.description}</p>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Selective filters */}
            {workflowForm.scope === "selective" && (
              <>
                <div className="space-y-2">
                  <Label>Document Types (optional)</Label>
                  <div className="grid grid-cols-2 gap-2">
                    {DOCUMENT_TYPES.map(type => (
                      <div
                        key={type.value}
                        className="flex items-center gap-2 p-2 border rounded cursor-pointer hover:bg-accent/50"
                        onClick={() => toggleDocumentType(type.value)}
                      >
                        <Checkbox
                          checked={workflowForm.document_types.includes(type.value)}
                          onCheckedChange={() => toggleDocumentType(type.value)}
                        />
                        <span className="text-sm">{type.label}</span>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="space-y-2">
                  <Label>Projects (optional)</Label>
                  <div className="max-h-40 overflow-y-auto space-y-2">
                    {projects.length === 0 ? (
                      <p className="text-sm text-muted-foreground">No projects available</p>
                    ) : (
                      projects.map(project => (
                        <div
                          key={project.project_id}
                          className="flex items-center gap-2 p-2 border rounded cursor-pointer hover:bg-accent/50"
                          onClick={() => toggleProject(project.project_id)}
                        >
                          <Checkbox
                            checked={workflowForm.project_ids.includes(project.project_id)}
                            onCheckedChange={() => toggleProject(project.project_id)}
                          />
                          <span className="text-sm">{project.name}</span>
                        </div>
                      ))
                    )}
                  </div>
                </div>
              </>
            )}

            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label>Active</Label>
                <p className="text-sm text-muted-foreground">Enable this workflow</p>
              </div>
              <Switch
                checked={workflowForm.active}
                onCheckedChange={(checked) => setWorkflowForm(prev => ({ ...prev, active: checked }))}
              />
            </div>

            <div className="flex justify-end gap-2 pt-4">
              <Button variant="outline" onClick={() => setWorkflowDialogOpen(false)}>Cancel</Button>
              <Button onClick={handleSaveWorkflow} disabled={saving} data-testid="save-doc-workflow-btn">
                {saving && <LoadingSpinner size="sm" className="mr-2" />}
                {editingWorkflow ? "Update" : "Create"}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* Create/Edit Rule Dialog */}
      <Dialog open={ruleDialogOpen} onOpenChange={setRuleDialogOpen}>
        <DialogContent className="max-w-lg max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{editingRule ? "Edit Rule" : "Add Approval Rule"}</DialogTitle>
            <DialogDescription>
              Define which document status transition requires approval
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 pt-4">
            {/* Status Transition */}
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>From Status</Label>
                <Select
                  value={ruleForm.from_status}
                  onValueChange={(value) => setRuleForm(prev => ({ ...prev, from_status: value }))}
                >
                  <SelectTrigger data-testid="doc-from-status-select">
                    <SelectValue placeholder="Select status" />
                  </SelectTrigger>
                  <SelectContent>
                    {DOCUMENT_STATUSES.map((status) => (
                      <SelectItem key={status.value} value={status.value}>
                        <div className="flex items-center gap-2">
                          <div
                            className="w-2 h-2 rounded-full"
                            style={{ backgroundColor: status.color }}
                          />
                          {status.label}
                        </div>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label>To Status</Label>
                <Select
                  value={ruleForm.to_status}
                  onValueChange={(value) => setRuleForm(prev => ({ ...prev, to_status: value }))}
                >
                  <SelectTrigger data-testid="doc-to-status-select">
                    <SelectValue placeholder="Select status" />
                  </SelectTrigger>
                  <SelectContent>
                    {DOCUMENT_STATUSES.map((status) => (
                      <SelectItem key={status.value} value={status.value}>
                        <div className="flex items-center gap-2">
                          <div
                            className="w-2 h-2 rounded-full"
                            style={{ backgroundColor: status.color }}
                          />
                          {status.label}
                        </div>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            {/* Rule Description */}
            <div className="space-y-2">
              <Label>Description (optional)</Label>
              <Input
                placeholder="Describe when this rule applies"
                value={ruleForm.description}
                onChange={(e) => setRuleForm(prev => ({ ...prev, description: e.target.value }))}
              />
            </div>

            {/* Approval Type */}
            <div className="space-y-2">
              <Label>Approval Type</Label>
              <Select
                value={ruleForm.approval_type}
                onValueChange={(value) => setRuleForm(prev => ({ ...prev, approval_type: value }))}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {APPROVAL_TYPES.map((type) => (
                    <SelectItem key={type.value} value={type.value}>
                      <div>
                        <p>{type.label}</p>
                        <p className="text-xs text-muted-foreground">{type.description}</p>
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Approver Role */}
            <div className="space-y-2">
              <Label>Approver Role</Label>
              <Select
                value={ruleForm.approver_role}
                onValueChange={(value) => setRuleForm(prev => ({ ...prev, approver_role: value }))}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {APPROVER_ROLES.map((role) => (
                    <SelectItem key={role.value} value={role.value}>
                      {role.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Timeout */}
            <div className="space-y-2">
              <Label>Timeout (minutes)</Label>
              <div className="flex items-center gap-4">
                <Input
                  type="number"
                  min="0"
                  placeholder="No timeout"
                  value={ruleForm.approval_timeout_minutes || ""}
                  onChange={(e) => setRuleForm(prev => ({
                    ...prev,
                    approval_timeout_minutes: e.target.value ? parseInt(e.target.value) : null
                  }))}
                  className="w-32"
                />
                {ruleForm.approval_timeout_minutes && (
                  <div className="flex items-center gap-2">
                    <Switch
                      checked={ruleForm.auto_approve_on_timeout}
                      onCheckedChange={(checked) => setRuleForm(prev => ({
                        ...prev,
                        auto_approve_on_timeout: checked
                      }))}
                    />
                    <Label className="font-normal">Auto-approve on timeout</Label>
                  </div>
                )}
              </div>
            </div>

            {/* SLA Pause */}
            <div className="flex items-center justify-between">
              <div>
                <Label>Pause SLA</Label>
                <p className="text-xs text-muted-foreground">Pause SLA timers while approval is pending</p>
              </div>
              <Switch
                checked={ruleForm.pause_sla}
                onCheckedChange={(checked) => setRuleForm(prev => ({ ...prev, pause_sla: checked }))}
              />
            </div>

            {/* Notifications */}
            <div className="space-y-3 border-t pt-4">
              <Label>Notifications</Label>
              <div className="flex items-center justify-between">
                <span className="text-sm">Notify approvers when approval is requested</span>
                <Switch
                  checked={ruleForm.notify_on_request}
                  onCheckedChange={(checked) => setRuleForm(prev => ({
                    ...prev,
                    notify_on_request: checked
                  }))}
                />
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm">Notify requester when approval is resolved</span>
                <Switch
                  checked={ruleForm.notify_on_resolution}
                  onCheckedChange={(checked) => setRuleForm(prev => ({
                    ...prev,
                    notify_on_resolution: checked
                  }))}
                />
              </div>
            </div>

            <div className="flex justify-end gap-2 pt-4">
              <Button variant="outline" onClick={() => setRuleDialogOpen(false)}>Cancel</Button>
              <Button onClick={handleSaveRule} disabled={saving} data-testid="save-doc-rule-btn">
                {saving && <LoadingSpinner size="sm" className="mr-2" />}
                {editingRule ? "Update Rule" : "Add Rule"}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation */}
      <AlertDialog open={deleteDialog.open} onOpenChange={(open) => setDeleteDialog({ ...deleteDialog, open })}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>
              Delete {deleteDialog.type === "workflow" ? "Workflow" : "Rule"}?
            </AlertDialogTitle>
            <AlertDialogDescription>
              {deleteDialog.type === "workflow" 
                ? `Are you sure you want to delete the "${deleteDialog.item?.name}" workflow? All rules will also be deleted.`
                : `Are you sure you want to delete this approval rule?`
              }
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={deleteDialog.type === "workflow" ? handleDeleteWorkflow : handleDeleteRule}
              disabled={deleting}
              className="bg-destructive text-destructive-foreground"
            >
              {deleting ? <LoadingSpinner size="sm" /> : "Delete"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}

export default DocumentWorkflowSettings;
