/**
 * TaskListView - List view for tasks
 */
import { Card, CardContent } from "../ui/card";
import { Badge } from "../ui/badge";
import { Avatar, AvatarFallback, AvatarImage } from "../ui/avatar";
import { Checkbox } from "../ui/checkbox";
import { Button } from "../ui/button";
import { CheckCircle2, Circle, Calendar, AlertTriangle, Plus } from "lucide-react";
import { format, isValid } from "date-fns";

const PRIORITIES = [
  { id: "low", label: "Low", color: "bg-green-500" },
  { id: "medium", label: "Medium", color: "bg-yellow-500" },
  { id: "high", label: "High", color: "bg-orange-500" },
  { id: "urgent", label: "Urgent", color: "bg-red-500" },
];

const safeFormat = (dateStr, formatStr) => {
  if (!dateStr) return null;
  try {
    const date = new Date(dateStr);
    if (!isValid(date)) return null;
    return format(date, formatStr);
  } catch {
    return null;
  }
};

export function TaskListView({
  tasks,
  statuses,
  members,
  selectedTaskIds = [],
  onTaskClick,
  onTaskSelect,
  onStatusToggle,
  onCreateTask,
}) {
  const getMemberById = (userId) => members.find((m) => m.user_id === userId);

  const isTaskBlocked = (task) => {
    if (!task.blocked_by || task.blocked_by.length === 0) return false;
    return task.blocked_by.some((depId) => {
      const depTask = tasks.find((t) => t.task_id === depId);
      return depTask && depTask.status !== "done";
    });
  };

  const getPriorityBadge = (priority) => {
    const p = PRIORITIES.find((pr) => pr.id === priority);
    return (
      <Badge variant="outline" className="text-xs">
        <span className={`w-2 h-2 rounded-full ${p?.color} mr-1`} />
        {p?.label || priority}
      </Badge>
    );
  };

  if (tasks.length === 0) {
    return (
      <Card>
        <CardContent className="p-0">
          <div className="empty-state py-12">
            <CheckCircle2 className="empty-state-icon" />
            <p className="text-muted-foreground">No tasks yet</p>
            <Button className="mt-4" onClick={onCreateTask}>
              <Plus className="w-4 h-4 mr-2" />
              Create Task
            </Button>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardContent className="p-0">
        <div className="divide-y divide-border">
          {tasks.map((task) => (
            <div
              key={task.task_id}
              className={`flex items-center gap-4 p-4 hover:bg-accent cursor-pointer transition-colors ${
                isTaskBlocked(task) ? "border-l-4 border-l-orange-500" : ""
              } ${selectedTaskIds.includes(task.task_id) ? "bg-primary/5" : ""}`}
              onClick={() => onTaskClick(task)}
              data-testid={`task-row-${task.task_id}`}
            >
              {/* Selection Checkbox */}
              <Checkbox
                checked={selectedTaskIds.includes(task.task_id)}
                onCheckedChange={(checked) => onTaskSelect(task.task_id, checked)}
                onClick={(e) => e.stopPropagation()}
                data-testid={`task-list-select-${task.task_id}`}
              />
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onStatusToggle(task.task_id, task.status);
                }}
                className="flex-shrink-0"
              >
                {task.status === "done" ? (
                  <CheckCircle2 className="w-5 h-5 text-green-500" />
                ) : (
                  <Circle className="w-5 h-5 text-muted-foreground" />
                )}
              </button>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <h4
                    className={`font-medium ${
                      task.status === "done" ? "line-through text-muted-foreground" : ""
                    }`}
                  >
                    {task.title}
                  </h4>
                  {isTaskBlocked(task) && (
                    <Badge variant="outline" className="text-orange-500 border-orange-500 text-xs">
                      <AlertTriangle className="w-3 h-3 mr-1" />
                      Blocked
                    </Badge>
                  )}
                </div>
                {task.description && (
                  <p className="text-sm text-muted-foreground truncate">
                    {task.description.replace(/<[^>]*>/g, "")}
                  </p>
                )}
              </div>
              <div className="flex items-center gap-3">
                {task.assignee_ids?.length > 0 && (
                  <div className="flex -space-x-1">
                    {task.assignee_ids.slice(0, 2).map((id) => {
                      const member = getMemberById(id);
                      return member ? (
                        <Avatar key={id} className="w-6 h-6 border-2 border-card">
                          <AvatarImage src={member.picture} />
                          <AvatarFallback className="text-[10px]">
                            {member.name?.charAt(0)}
                          </AvatarFallback>
                        </Avatar>
                      ) : null;
                    })}
                  </div>
                )}
                {getPriorityBadge(task.priority)}
                <Badge variant="outline">
                  {statuses.find((s) => s.id === task.status)?.label}
                </Badge>
                {task.due_date && (
                  <span className="text-sm text-muted-foreground flex items-center gap-1">
                    <Calendar className="w-3.5 h-3.5" />
                    {safeFormat(task.due_date, "MMM d") || "No date"}
                  </span>
                )}
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
