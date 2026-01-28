/**
 * TaskCard - Compact task card for Kanban board
 */
import { useMemo } from "react";
import { Badge } from "../ui/badge";
import { Avatar, AvatarFallback, AvatarImage } from "../ui/avatar";
import { Calendar, CheckCircle2, AlertTriangle, GripVertical } from "lucide-react";
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

export function TaskCard({ 
  task, 
  members = [], 
  isBlocked = false,
  onClick,
  isDragging = false,
  dragHandleProps = {},
}) {
  const priority = useMemo(() => 
    PRIORITIES.find(p => p.id === task.priority), 
    [task.priority]
  );
  
  const assignees = useMemo(() => 
    (task.assignee_ids || [])
      .map(id => members.find(m => m.user_id === id))
      .filter(Boolean)
      .slice(0, 3),
    [task.assignee_ids, members]
  );

  const checklistProgress = useMemo(() => {
    if (!task.checklist || task.checklist.length === 0) return null;
    const completed = task.checklist.filter(item => item.completed).length;
    return { completed, total: task.checklist.length };
  }, [task.checklist]);

  return (
    <div
      className={`bg-card border rounded-lg p-3 cursor-pointer hover:shadow-md transition-shadow ${
        isDragging ? 'shadow-lg ring-2 ring-primary' : ''
      } ${isBlocked ? 'opacity-70 border-destructive/50' : ''}`}
      onClick={onClick}
      data-testid={`task-card-${task.task_id}`}
    >
      <div className="flex items-start gap-2">
        <div {...dragHandleProps} className="mt-1 cursor-grab active:cursor-grabbing">
          <GripVertical className="w-4 h-4 text-muted-foreground" />
        </div>
        <div className="flex-1 min-w-0">
          <h4 className="font-medium text-sm line-clamp-2">{task.title}</h4>
          
          <div className="flex items-center gap-2 mt-2 flex-wrap">
            {/* Priority Badge */}
            {priority && (
              <Badge variant="outline" className="text-xs">
                <span className={`w-2 h-2 rounded-full ${priority.color} mr-1`} />
                {priority.label}
              </Badge>
            )}
            
            {/* Due Date */}
            {task.due_date && (
              <span className="text-xs text-muted-foreground flex items-center gap-1">
                <Calendar className="w-3 h-3" />
                {safeFormat(task.due_date, "MMM d")}
              </span>
            )}
            
            {/* Blocked Indicator */}
            {isBlocked && (
              <Badge variant="destructive" className="text-xs">
                <AlertTriangle className="w-3 h-3 mr-1" />
                Blocked
              </Badge>
            )}
            
            {/* Checklist Progress */}
            {checklistProgress && (
              <Badge variant="secondary" className="text-xs">
                <CheckCircle2 className="w-3 h-3 mr-1" />
                {checklistProgress.completed}/{checklistProgress.total}
              </Badge>
            )}
          </div>
          
          {/* Assignees */}
          {assignees.length > 0 && (
            <div className="flex items-center gap-1 mt-2">
              <div className="flex -space-x-2">
                {assignees.map((member) => (
                  <Avatar key={member.user_id} className="w-6 h-6 border-2 border-background">
                    <AvatarImage src={member.picture} />
                    <AvatarFallback className="text-[10px]">
                      {member.name?.charAt(0)}
                    </AvatarFallback>
                  </Avatar>
                ))}
              </div>
              {task.assignee_ids?.length > 3 && (
                <span className="text-xs text-muted-foreground ml-1">
                  +{task.assignee_ids.length - 3}
                </span>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
