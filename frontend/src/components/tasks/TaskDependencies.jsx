/**
 * TaskDependencies - Dependencies management for task detail
 */
import { useMemo } from "react";
import { Badge } from "../ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../ui/select";
import { 
  GitBranch, 
  AlertTriangle, 
  CheckCircle2, 
  Circle, 
  X,
  ArrowRight
} from "lucide-react";

export function TaskDependencies({
  task,
  allTasks = [],
  canEdit = true,
  onUpdateDependencies,
}) {
  const blockedByTasks = useMemo(() => 
    (task.blocked_by || [])
      .map(id => allTasks.find(t => t.task_id === id))
      .filter(Boolean),
    [task.blocked_by, allTasks]
  );

  const blocksTasks = useMemo(() => 
    (task.blocks || [])
      .map(id => allTasks.find(t => t.task_id === id))
      .filter(Boolean),
    [task.blocks, allTasks]
  );

  const availableBlockers = useMemo(() => 
    allTasks.filter(t => 
      t.task_id !== task.task_id && 
      !task.blocked_by?.includes(t.task_id) &&
      !task.blocks?.includes(t.task_id)
    ),
    [allTasks, task]
  );

  const availableBlocks = useMemo(() => 
    allTasks.filter(t => 
      t.task_id !== task.task_id && 
      !task.blocks?.includes(t.task_id) &&
      !task.blocked_by?.includes(t.task_id)
    ),
    [allTasks, task]
  );

  const handleRemoveBlockedBy = (depId) => {
    onUpdateDependencies?.(
      (task.blocked_by || []).filter(id => id !== depId),
      task.blocks || []
    );
  };

  const handleAddBlockedBy = (depId) => {
    if (depId && !task.blocked_by?.includes(depId)) {
      onUpdateDependencies?.(
        [...(task.blocked_by || []), depId],
        task.blocks || []
      );
    }
  };

  const handleRemoveBlocks = (depId) => {
    onUpdateDependencies?.(
      task.blocked_by || [],
      (task.blocks || []).filter(id => id !== depId)
    );
  };

  const handleAddBlocks = (depId) => {
    if (depId && !task.blocks?.includes(depId)) {
      onUpdateDependencies?.(
        task.blocked_by || [],
        [...(task.blocks || []), depId]
      );
    }
  };

  const totalDeps = (task.blocked_by?.length || 0) + (task.blocks?.length || 0);

  return (
    <div className="space-y-4">
      <h4 className="text-sm font-medium flex items-center gap-2">
        <GitBranch className="w-4 h-4" />
        Dependencies
        {totalDeps > 0 && (
          <Badge variant="secondary" className="text-xs">
            {totalDeps}
          </Badge>
        )}
      </h4>

      {/* Blocked By Section */}
      <div className="space-y-2">
        <p className="text-xs text-muted-foreground flex items-center gap-1">
          <AlertTriangle className="w-3 h-3" />
          Blocked by (this task waits for):
        </p>
        
        <div className="flex flex-wrap gap-2">
          {blockedByTasks.map(depTask => (
            <Badge
              key={depTask.task_id}
              variant={depTask.status === 'done' ? 'secondary' : 'destructive'}
              className="flex items-center gap-1 pr-1"
            >
              {depTask.status === 'done' ? (
                <CheckCircle2 className="w-3 h-3" />
              ) : (
                <Circle className="w-3 h-3" />
              )}
              <span className="max-w-[150px] truncate">{depTask.title}</span>
              {canEdit && (
                <button
                  onClick={() => handleRemoveBlockedBy(depTask.task_id)}
                  className="ml-1 hover:bg-background/20 rounded p-0.5"
                >
                  <X className="w-3 h-3" />
                </button>
              )}
            </Badge>
          ))}
        </div>

        {canEdit && availableBlockers.length > 0 && (
          <Select value="" onValueChange={handleAddBlockedBy}>
            <SelectTrigger className="w-full h-8 text-sm">
              <SelectValue placeholder="+ Add blocking task..." />
            </SelectTrigger>
            <SelectContent>
              {availableBlockers.map(t => (
                <SelectItem key={t.task_id} value={t.task_id}>
                  <span className="truncate">{t.title}</span>
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        )}
      </div>

      {/* Blocks Section */}
      <div className="space-y-2">
        <p className="text-xs text-muted-foreground flex items-center gap-1">
          <ArrowRight className="w-3 h-3" />
          Blocks (tasks waiting for this):
        </p>
        
        <div className="flex flex-wrap gap-2">
          {blocksTasks.map(depTask => (
            <Badge
              key={depTask.task_id}
              variant="outline"
              className="flex items-center gap-1 pr-1"
            >
              {depTask.status === 'done' ? (
                <CheckCircle2 className="w-3 h-3" />
              ) : (
                <Circle className="w-3 h-3" />
              )}
              <span className="max-w-[150px] truncate">{depTask.title}</span>
              {canEdit && (
                <button
                  onClick={() => handleRemoveBlocks(depTask.task_id)}
                  className="ml-1 hover:bg-muted rounded p-0.5"
                >
                  <X className="w-3 h-3" />
                </button>
              )}
            </Badge>
          ))}
        </div>

        {canEdit && availableBlocks.length > 0 && (
          <Select value="" onValueChange={handleAddBlocks}>
            <SelectTrigger className="w-full h-8 text-sm">
              <SelectValue placeholder="+ Add blocked task..." />
            </SelectTrigger>
            <SelectContent>
              {availableBlocks.map(t => (
                <SelectItem key={t.task_id} value={t.task_id}>
                  <span className="truncate">{t.title}</span>
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        )}
      </div>

      {/* Empty State */}
      {totalDeps === 0 && !canEdit && (
        <p className="text-sm text-muted-foreground text-center py-2">
          No dependencies
        </p>
      )}
    </div>
  );
}
