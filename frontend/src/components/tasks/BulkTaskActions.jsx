/**
 * BulkTaskActions - Bulk action toolbar for selected tasks
 */
import { useState } from "react";
import { Button } from "../ui/button";
import { Badge } from "../ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../ui/select";
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
  X, 
  Trash2, 
  UserPlus, 
  ArrowRight,
  CheckCircle2
} from "lucide-react";
import { toast } from "sonner";

const PRIORITIES = [
  { id: "low", label: "Low" },
  { id: "medium", label: "Medium" },
  { id: "high", label: "High" },
  { id: "urgent", label: "Urgent" },
];

export function BulkTaskActions({
  selectedTaskIds = [],
  tasks = [],
  members = [],
  statuses = [],
  onClearSelection,
  onBulkUpdate,
  onBulkDelete,
  onBulkAssign,
}) {
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [processing, setProcessing] = useState(false);

  const selectedCount = selectedTaskIds.length;
  
  if (selectedCount === 0) return null;

  const handleStatusChange = async (status) => {
    setProcessing(true);
    try {
      await onBulkUpdate?.(selectedTaskIds, { status });
      toast.success(`Updated ${selectedCount} task(s) to ${status}`);
      onClearSelection?.();
    } catch (error) {
      toast.error("Failed to update tasks");
    } finally {
      setProcessing(false);
    }
  };

  const handlePriorityChange = async (priority) => {
    setProcessing(true);
    try {
      await onBulkUpdate?.(selectedTaskIds, { priority });
      toast.success(`Updated priority for ${selectedCount} task(s)`);
      onClearSelection?.();
    } catch (error) {
      toast.error("Failed to update tasks");
    } finally {
      setProcessing(false);
    }
  };

  const handleAssign = async (userId) => {
    setProcessing(true);
    try {
      await onBulkAssign?.(selectedTaskIds, userId);
      const member = members.find(m => m.user_id === userId);
      toast.success(`Assigned ${selectedCount} task(s) to ${member?.name || 'user'}`);
      onClearSelection?.();
    } catch (error) {
      toast.error("Failed to assign tasks");
    } finally {
      setProcessing(false);
    }
  };

  const handleDelete = async () => {
    setProcessing(true);
    try {
      await onBulkDelete?.(selectedTaskIds);
      toast.success(`Deleted ${selectedCount} task(s)`);
      onClearSelection?.();
      setDeleteDialogOpen(false);
    } catch (error) {
      toast.error("Failed to delete tasks");
    } finally {
      setProcessing(false);
    }
  };

  return (
    <>
      <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-50 animate-in slide-in-from-bottom-4" data-testid="bulk-actions-toolbar">
        <div className="flex items-center gap-2 px-4 py-3 bg-background border rounded-lg shadow-lg">
          {/* Selection Count */}
          <Badge variant="secondary" className="mr-2" data-testid="bulk-selected-count">
            {selectedCount} selected
          </Badge>

          {/* Change Status */}
          <Select onValueChange={handleStatusChange} disabled={processing}>
            <SelectTrigger className="w-[140px] h-8" data-testid="bulk-status-trigger">
              <ArrowRight className="w-4 h-4 mr-1" />
              <SelectValue placeholder="Status" />
            </SelectTrigger>
            <SelectContent>
              {statuses.map(s => (
                <SelectItem key={s.id} value={s.id} data-testid={`bulk-status-${s.id}`}>
                  <div className="flex items-center gap-2">
                    <div 
                      className="w-2 h-2 rounded-full" 
                      style={{ backgroundColor: s.color }}
                    />
                    {s.label}
                  </div>
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          {/* Change Priority */}
          <Select onValueChange={handlePriorityChange} disabled={processing}>
            <SelectTrigger className="w-[130px] h-8" data-testid="bulk-priority-trigger">
              <CheckCircle2 className="w-4 h-4 mr-1" />
              <SelectValue placeholder="Priority" />
            </SelectTrigger>
            <SelectContent>
              {PRIORITIES.map(p => (
                <SelectItem key={p.id} value={p.id} data-testid={`bulk-priority-${p.id}`}>{p.label}</SelectItem>
              ))}
            </SelectContent>
          </Select>

          {/* Assign To */}
          <Select onValueChange={handleAssign} disabled={processing}>
            <SelectTrigger className="w-[140px] h-8" data-testid="bulk-assign-trigger">
              <UserPlus className="w-4 h-4 mr-1" />
              <SelectValue placeholder="Assign to" />
            </SelectTrigger>
            <SelectContent>
              {members.map(m => (
                <SelectItem key={m.user_id} value={m.user_id} data-testid={`bulk-assign-${m.user_id}`}>
                  {m.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          {/* Delete */}
          <Button
            variant="destructive"
            size="sm"
            onClick={() => setDeleteDialogOpen(true)}
            disabled={processing}
            data-testid="bulk-delete-btn"
          >
            <Trash2 className="w-4 h-4 mr-1" />
            Delete
          </Button>

          {/* Clear Selection */}
          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8"
            onClick={onClearSelection}
            data-testid="bulk-clear-selection-btn"
          >
            <X className="w-4 h-4" />
          </Button>
        </div>
      </div>

      {/* Delete Confirmation */}
      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete {selectedCount} Task(s)?</AlertDialogTitle>
            <AlertDialogDescription>
              This action cannot be undone. All selected tasks and their checklists, 
              comments, and attachments will be permanently deleted.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDelete}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
              disabled={processing}
            >
              {processing ? "Deleting..." : "Delete Tasks"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}
