/**
 * TaskListItem - Row-style task item for list view
 */
import { useMemo } from "react";
import { Badge } from "../ui/badge";
import { Avatar, AvatarFallback, AvatarImage } from "../ui/avatar";
import { Checkbox } from "../ui/checkbox";
import { Calendar, CheckCircle2, AlertTriangle } from "lucide-react";
import { format, isValid, parseISO } from "date-fns";

const PRIORITIES = [
  { id: "low", label: "Low", color: "bg-green-500" },
  { id: "medium", label: "Medium", color: "bg-yellow-500" },
  { id: "high", label: "High", color: "bg-orange-500" },
  { id: "urgent", label: "Urgent", color: "bg-red-500" },
];

const safeFormat = (dateStr, formatStr) => {
  if (!dateStr) return null;
  try {
    const date = typeof dateStr === 'string' ? parseISO(dateStr) : dateStr;
    return isValid(date) ? format(date, formatStr) : null;
  } catch {
    return null;
  }
};

export function TaskListItem({ 
  task, 
  members = [], 
  statuses = [],
  isBlocked = false,
  isSelected = false,
  onSelect,
  onClick,
  onStatusChange,
}) {
  const priority = useMemo(() => 
    PRIORITIES.find(p => p.id === task.priority), 
    [task.priority]
  );
  
  const status = useMemo(() => 
    statuses.find(s => s.id === task.status),
    [task.status, statuses]
  );
  
  const assignees = useMemo(() => 
    (task.assignee_ids || [])
      .map(id => members.find(m => m.user_id === id))
      .filter(Boolean),
    [task.assignee_ids, members]
  );

  const checklistProgress = useMemo(() => {
    if (!task.checklist || task.checklist.length === 0) return null;
    const completed = task.checklist.filter(item => item.completed).length;
    return { completed, total: task.checklist.length };
  }, [task.checklist]);

  return (
    <div
      className={`flex items-center gap-3 p-3 border-b hover:bg-muted/50 transition-colors cursor-pointer ${
        isBlocked ? 'opacity-70 bg-destructive/5' : ''
      } ${isSelected ? 'bg-primary/5' : ''}`}
      onClick={onClick}
      data-testid={`task-list-item-${task.task_id}`}
    >
      {/* Selection Checkbox */}
      {onSelect && (
        <Checkbox
          checked={isSelected}
          onCheckedChange={(checked) => {
            onSelect(task.task_id, checked);
          }}
          onClick={(e) => e.stopPropagation()}
          data-testid={`task-checkbox-${task.task_id}`}
        />
      )}
      
      {/* Status Indicator */}
      <div
        className="w-3 h-3 rounded-full shrink-0"
        style={{ backgroundColor: status?.color || '#6b7280' }}
      />
      
      {/* Task Title */}
      <div className="flex-1 min-w-0">
        <h4 className={`font-medium text-sm truncate ${
          task.status === "done" ? "line-through text-muted-foreground" : ""
        }`}>
          {task.title}
        </h4>
      </div>
      
      {/* Priority Badge */}
      {priority && (
        <Badge variant="outline" className="text-xs shrink-0">
          <span className={`w-2 h-2 rounded-full ${priority.color} mr-1`} />
          {priority.label}
        </Badge>
      )}
      
      {/* Blocked Indicator */}
      {isBlocked && (
        <Badge variant="destructive" className="text-xs shrink-0">
          <AlertTriangle className="w-3 h-3" />
        </Badge>
      )}
      
      {/* Checklist Progress */}
      {checklistProgress && (
        <Badge variant="secondary" className="text-xs shrink-0">
          <CheckCircle2 className="w-3 h-3 mr-1" />
          {checklistProgress.completed}/{checklistProgress.total}
        </Badge>
      )}
      
      {/* Due Date */}
      {task.due_date && (
        <span className="text-xs text-muted-foreground flex items-center gap-1 shrink-0">
          <Calendar className="w-3 h-3" />
          {safeFormat(task.due_date, "MMM d")}
        </span>
      )}
      
      {/* Assignees */}
      <div className="flex -space-x-2 shrink-0">
        {assignees.slice(0, 3).map((member) => (
          <Avatar key={member.user_id} className="w-6 h-6 border-2 border-background">
            <AvatarImage src={member.picture} />
            <AvatarFallback className="text-[10px]">
              {member.name?.charAt(0)}
            </AvatarFallback>
          </Avatar>
        ))}
        {assignees.length > 3 && (
          <div className="w-6 h-6 rounded-full bg-muted border-2 border-background flex items-center justify-center">
            <span className="text-[10px] text-muted-foreground">
              +{assignees.length - 3}
            </span>
          </div>
        )}
      </div>
    </div>
  );
}
