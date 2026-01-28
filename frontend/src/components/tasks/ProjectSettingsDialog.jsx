/**
 * ProjectSettingsDialog - Modal for project settings (statuses, workflows)
 */
import { useState, useMemo } from "react";
import { Button } from "../ui/button";
import { Input } from "../ui/input";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "../ui/dialog";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../ui/tabs";
import { ProjectWorkflowView } from "../settings";
import { Plus, Trash2 } from "lucide-react";

const DEFAULT_STATUSES = [
  { id: "todo", label: "To Do", color: "#64748b" },
  { id: "in_progress", label: "In Progress", color: "#3b82f6" },
  { id: "review", label: "In Review", color: "#a855f7" },
  { id: "done", label: "Done", color: "#22c55e" },
];

export function ProjectSettingsDialog({
  open,
  onOpenChange,
  projectId,
  initialStatuses = DEFAULT_STATUSES,
  onSaveStatuses,
}) {
  // Use initialStatuses directly and track local changes
  const [localStatuses, setLocalStatuses] = useState(null);
  
  // Current statuses: use local changes if any, otherwise initial
  const statuses = useMemo(() => {
    return localStatuses !== null ? localStatuses : initialStatuses;
  }, [localStatuses, initialStatuses]);

  const handleSave = async () => {
    await onSaveStatuses(statuses);
    setLocalStatuses(null); // Reset local changes
  };

  const handleCancel = () => {
    setLocalStatuses(null); // Discard local changes
    onOpenChange(false);
  };

  const handleAddStatus = () => {
    setLocalStatuses([
      ...statuses,
      { id: `status_${Date.now()}`, label: "New Status", color: "#6b7280" },
    ]);
  };

  const handleRemoveStatus = (index) => {
    setLocalStatuses(statuses.filter((_, i) => i !== index));
  };

  const handleUpdateStatus = (index, field, value) => {
    const updated = [...statuses];
    updated[index] = { ...updated[index], [field]: value };
    setLocalStatuses(updated);
  };

  // Reset local changes when dialog closes
  const handleOpenChange = (isOpen) => {
    if (!isOpen) {
      setLocalStatuses(null);
    }
    onOpenChange(isOpen);
  };

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="max-w-2xl max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Project Settings</DialogTitle>
        </DialogHeader>
        <Tabs defaultValue="statuses" className="mt-4">
          <TabsList className="w-full">
            <TabsTrigger value="statuses" className="flex-1">
              Task Statuses
            </TabsTrigger>
            <TabsTrigger value="workflows" className="flex-1">
              Approval Workflows
            </TabsTrigger>
          </TabsList>

          <TabsContent value="statuses" className="space-y-4 pt-4">
            <p className="text-sm text-muted-foreground">
              Customize task statuses for this project&apos;s workflow.
            </p>
            <div className="space-y-3">
              {statuses.map((status, index) => (
                <div key={status.id} className="flex items-center gap-2">
                  <input
                    type="color"
                    value={status.color}
                    onChange={(e) => handleUpdateStatus(index, "color", e.target.value)}
                    className="w-8 h-8 rounded cursor-pointer"
                  />
                  <Input
                    value={status.label}
                    onChange={(e) => handleUpdateStatus(index, "label", e.target.value)}
                    className="flex-1"
                  />
                  {statuses.length > 2 && (
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => handleRemoveStatus(index)}
                    >
                      <Trash2 className="w-4 h-4" />
                    </Button>
                  )}
                </div>
              ))}
            </div>
            <Button variant="outline" onClick={handleAddStatus} className="w-full">
              <Plus className="w-4 h-4 mr-2" />
              Add Status
            </Button>
            <div className="flex justify-end gap-2 pt-4">
              <Button variant="outline" onClick={handleCancel}>
                Cancel
              </Button>
              <Button onClick={handleSave}>Save Changes</Button>
            </div>
          </TabsContent>

          <TabsContent value="workflows" className="pt-4">
            <ProjectWorkflowView projectId={projectId} />
          </TabsContent>
        </Tabs>
      </DialogContent>
    </Dialog>
  );
}
