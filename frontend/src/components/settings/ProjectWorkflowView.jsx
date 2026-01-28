/**
 * ProjectWorkflowView - Read-only view of workflows that apply to a project
 * For Project Settings (non-admin view)
 */
import { useState, useEffect } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../ui/card";
import { Badge } from "../ui/badge";
import { LoadingSpinner } from "../ui/loading-spinner";
import { GitBranch, Globe, FolderOpen, ArrowRight, Users, Clock, Info } from "lucide-react";
import { getApplicableWorkflowsForProject } from "../../api/workflows";

export function ProjectWorkflowView({ projectId }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (projectId) {
      loadData();
    }
  }, [projectId]);

  const loadData = async () => {
    try {
      setLoading(true);
      const result = await getApplicableWorkflowsForProject(projectId);
      setData(result);
    } catch (error) {
      console.error("Failed to load workflows:", error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-8">
        <LoadingSpinner />
      </div>
    );
  }

  if (!data) {
    return null;
  }

  const { global_workflow, selective_workflows, effective_workflow } = data;
  const hasWorkflows = global_workflow || selective_workflows?.length > 0;

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <GitBranch className="w-4 h-4" />
            Applied Approval Workflows
          </CardTitle>
          <CardDescription>
            Workflows that control task status transitions in this project
          </CardDescription>
        </CardHeader>
        <CardContent>
          {!hasWorkflows ? (
            <div className="text-center py-6 text-muted-foreground">
              <Info className="w-8 h-8 mx-auto mb-2 opacity-50" />
              <p className="text-sm">No approval workflows apply to this project</p>
              <p className="text-xs mt-1">Status changes don&apos;t require approval</p>
            </div>
          ) : (
            <div className="space-y-4">
              {/* Effective Workflow Highlight */}
              {effective_workflow && (
                <div className="p-4 border rounded-lg bg-primary/5 border-primary/20">
                  <div className="flex items-center gap-2 mb-2">
                    <Badge variant="default" className="text-xs">Active</Badge>
                    <span className="font-medium">{effective_workflow.name}</span>
                    <Badge variant={effective_workflow.scope === "global" ? "secondary" : "outline"} className="text-xs">
                      {effective_workflow.scope === "global" ? (
                        <><Globe className="w-3 h-3 mr-1" />Global</>
                      ) : (
                        <><FolderOpen className="w-3 h-3 mr-1" />Selective</>
                      )}
                    </Badge>
                  </div>
                  {effective_workflow.description && (
                    <p className="text-sm text-muted-foreground">{effective_workflow.description}</p>
                  )}
                  <p className="text-xs text-muted-foreground mt-2">
                    {effective_workflow.rules_count} approval rule{effective_workflow.rules_count !== 1 ? "s" : ""} defined
                  </p>
                </div>
              )}

              {/* Global Workflow Info */}
              {global_workflow && effective_workflow?.workflow_id !== global_workflow.workflow_id && (
                <div className="p-3 border rounded-lg">
                  <div className="flex items-center gap-2">
                    <Globe className="w-4 h-4 text-muted-foreground" />
                    <span className="text-sm">{global_workflow.name}</span>
                    <Badge variant="secondary" className="text-xs">Global</Badge>
                  </div>
                </div>
              )}

              {/* Selective Workflows */}
              {selective_workflows?.length > 0 && (
                <div className="space-y-2">
                  <p className="text-xs text-muted-foreground uppercase tracking-wide">Selective Workflows</p>
                  {selective_workflows.map((wf) => (
                    <div 
                      key={wf.workflow_id} 
                      className={`p-3 border rounded-lg ${effective_workflow?.workflow_id === wf.workflow_id ? 'border-primary/50' : ''}`}
                    >
                      <div className="flex items-center gap-2">
                        <FolderOpen className="w-4 h-4 text-muted-foreground" />
                        <span className="text-sm">{wf.name}</span>
                        {effective_workflow?.workflow_id === wf.workflow_id && (
                          <Badge variant="outline" className="text-xs">Active</Badge>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {/* Priority Note */}
              {global_workflow && selective_workflows?.length > 0 && (
                <p className="text-xs text-muted-foreground bg-muted/50 p-2 rounded">
                  <Info className="w-3 h-3 inline mr-1" />
                  Global workflows take priority over selective workflows
                </p>
              )}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
