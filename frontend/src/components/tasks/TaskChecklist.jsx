/**
 * TaskChecklist - Checklist/subtasks component for task detail
 */
import { useState } from "react";
import { Button } from "../ui/button";
import { Input } from "../ui/input";
import { Checkbox } from "../ui/checkbox";
import { Progress } from "../ui/progress";
import { Plus, Trash2, ListChecks } from "lucide-react";
import { toast } from "sonner";

export function TaskChecklist({
  taskId,
  checklist = [],
  canEdit = true,
  onAddItem,
  onUpdateItem,
  onDeleteItem,
}) {
  const [newItemText, setNewItemText] = useState("");
  const [adding, setAdding] = useState(false);

  const completedCount = checklist.filter(item => item.completed).length;
  const progress = checklist.length > 0 ? (completedCount / checklist.length) * 100 : 0;

  const handleAddItem = async () => {
    if (!newItemText.trim()) return;
    
    setAdding(true);
    try {
      await onAddItem?.(newItemText.trim());
      setNewItemText("");
    } catch (error) {
      toast.error("Failed to add checklist item");
    } finally {
      setAdding(false);
    }
  };

  const handleToggle = async (itemId, completed) => {
    try {
      await onUpdateItem?.(itemId, { completed });
    } catch (error) {
      toast.error("Failed to update checklist item");
    }
  };

  const handleDelete = async (itemId) => {
    try {
      await onDeleteItem?.(itemId);
    } catch (error) {
      toast.error("Failed to delete checklist item");
    }
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h4 className="text-sm font-medium flex items-center gap-2">
          <ListChecks className="w-4 h-4" />
          Checklist
          {checklist.length > 0 && (
            <span className="text-muted-foreground">
              ({completedCount}/{checklist.length})
            </span>
          )}
        </h4>
      </div>

      {/* Progress Bar */}
      {checklist.length > 0 && (
        <Progress value={progress} className="h-2" />
      )}

      {/* Checklist Items */}
      <div className="space-y-2">
        {checklist.map((item) => (
          <div
            key={item.item_id}
            className="flex items-center gap-2 group"
          >
            <Checkbox
              checked={item.completed}
              onCheckedChange={(checked) => handleToggle(item.item_id, checked)}
              disabled={!canEdit}
              data-testid={`checklist-item-${item.item_id}`}
            />
            <span
              className={`flex-1 text-sm ${
                item.completed ? 'line-through text-muted-foreground' : ''
              }`}
            >
              {item.title}
            </span>
            {canEdit && (
              <Button
                variant="ghost"
                size="icon"
                className="h-6 w-6 opacity-0 group-hover:opacity-100 transition-opacity"
                onClick={() => handleDelete(item.item_id)}
              >
                <Trash2 className="w-3 h-3 text-destructive" />
              </Button>
            )}
          </div>
        ))}
      </div>

      {/* Add New Item */}
      {canEdit && (
        <div className="flex gap-2">
          <Input
            placeholder="Add checklist item..."
            value={newItemText}
            onChange={(e) => setNewItemText(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') {
                handleAddItem();
              }
            }}
            className="h-8 text-sm"
            data-testid="checklist-new-item-input"
          />
          <Button
            size="sm"
            variant="outline"
            onClick={handleAddItem}
            disabled={adding || !newItemText.trim()}
            data-testid="checklist-add-btn"
          >
            <Plus className="w-4 h-4" />
          </Button>
        </div>
      )}

      {/* Empty State */}
      {checklist.length === 0 && !canEdit && (
        <p className="text-sm text-muted-foreground text-center py-2">
          No checklist items
        </p>
      )}
    </div>
  );
}
