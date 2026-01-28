/**
 * KanbanBoard - Drag-and-drop Kanban board for tasks
 */
import { DragDropContext, Droppable, Draggable } from "@hello-pangea/dnd";
import { Badge } from "../ui/badge";
import { Avatar, AvatarFallback, AvatarImage } from "../ui/avatar";
import { Checkbox } from "../ui/checkbox";
import { Button } from "../ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "../ui/dropdown-menu";
import { MoreHorizontal, Calendar, Trash2, AlertTriangle } from "lucide-react";
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

export function KanbanBoard({
  tasks,
  statuses,
  members,
  selectedTaskIds = [],
  canEditTask = true,
  canDeleteTask = true,
  onDragEnd,
  onTaskClick,
  onTaskSelect,
  onStatusChange,
  onDeleteTask,
}) {
  const getTasksByStatus = (statusId) => tasks.filter((t) => t.status === statusId);

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

  return (
    <DragDropContext onDragEnd={onDragEnd}>
      <div className="kanban-board">
        {statuses.map((status) => (
          <Droppable droppableId={status.id} key={status.id}>
            {(provided, snapshot) => (
              <div
                ref={provided.innerRef}
                {...provided.droppableProps}
                className={`kanban-column ${snapshot.isDraggingOver ? "bg-accent/50" : ""}`}
                data-testid={`kanban-column-${status.id}`}
              >
                <div className="kanban-header">
                  <div className="flex items-center gap-2">
                    <span
                      className="w-3 h-3 rounded-full"
                      style={{ backgroundColor: status.color }}
                    />
                    <h3 className="font-medium">{status.label}</h3>
                    <Badge variant="secondary" className="text-xs">
                      {getTasksByStatus(status.id).length}
                    </Badge>
                  </div>
                </div>
                <div className="kanban-cards min-h-[200px]">
                  {getTasksByStatus(status.id).map((task, index) => (
                    <Draggable key={task.task_id} draggableId={task.task_id} index={index}>
                      {(provided, snapshot) => (
                        <div
                          ref={provided.innerRef}
                          {...provided.draggableProps}
                          {...provided.dragHandleProps}
                          className={`kanban-card group relative ${
                            snapshot.isDragging ? "shadow-lg ring-2 ring-primary" : ""
                          } ${isTaskBlocked(task) ? "border-l-4 border-l-orange-500" : ""} ${
                            selectedTaskIds.includes(task.task_id)
                              ? "ring-2 ring-primary bg-primary/5"
                              : ""
                          }`}
                          onClick={() => onTaskClick(task)}
                          data-testid={`task-card-${task.task_id}`}
                        >
                          {/* Selection Checkbox */}
                          <div
                            className="absolute top-2 left-2 opacity-0 group-hover:opacity-100"
                            style={{
                              opacity:
                                selectedTaskIds.length > 0 ||
                                selectedTaskIds.includes(task.task_id)
                                  ? 1
                                  : undefined,
                            }}
                          >
                            <Checkbox
                              checked={selectedTaskIds.includes(task.task_id)}
                              onCheckedChange={(checked) => onTaskSelect(task.task_id, checked)}
                              onClick={(e) => e.stopPropagation()}
                              data-testid={`task-select-${task.task_id}`}
                            />
                          </div>
                          {isTaskBlocked(task) && (
                            <div className="flex items-center gap-1 text-orange-500 text-xs mb-2">
                              <AlertTriangle className="w-3 h-3" />
                              <span>Blocked</span>
                            </div>
                          )}
                          <div className="flex items-start justify-between gap-2 mb-2">
                            <h4 className="font-medium text-sm line-clamp-2">{task.title}</h4>
                            <DropdownMenu>
                              <DropdownMenuTrigger asChild>
                                <Button
                                  variant="ghost"
                                  size="icon"
                                  className="h-6 w-6"
                                  onClick={(e) => e.stopPropagation()}
                                >
                                  <MoreHorizontal className="w-4 h-4" />
                                </Button>
                              </DropdownMenuTrigger>
                              <DropdownMenuContent align="end">
                                {canEditTask &&
                                  statuses
                                    .filter((s) => s.id !== task.status)
                                    .map((s) => (
                                      <DropdownMenuItem
                                        key={s.id}
                                        onClick={(e) => {
                                          e.stopPropagation();
                                          onStatusChange(task.task_id, s.id);
                                        }}
                                      >
                                        Move to {s.label}
                                      </DropdownMenuItem>
                                    ))}
                                {canDeleteTask && (
                                  <DropdownMenuItem
                                    className="text-destructive"
                                    onClick={(e) => {
                                      e.stopPropagation();
                                      onDeleteTask(task.task_id);
                                    }}
                                  >
                                    <Trash2 className="w-4 h-4 mr-2" />
                                    Delete
                                  </DropdownMenuItem>
                                )}
                              </DropdownMenuContent>
                            </DropdownMenu>
                          </div>
                          {task.description && (
                            <p className="text-xs text-muted-foreground line-clamp-2 mb-2">
                              {task.description.replace(/<[^>]*>/g, "")}
                            </p>
                          )}
                          <div className="flex items-center justify-between">
                            {getPriorityBadge(task.priority)}
                            <div className="flex items-center gap-2">
                              {task.due_date && (
                                <span className="flex items-center gap-1 text-xs text-muted-foreground">
                                  <Calendar className="w-3 h-3" />
                                  {safeFormat(task.due_date, "MMM d") || "No date"}
                                </span>
                              )}
                            </div>
                          </div>
                          {/* Assignee Avatars */}
                          {task.assignee_ids?.length > 0 && (
                            <div className="flex -space-x-2 mt-2">
                              {task.assignee_ids.slice(0, 3).map((id) => {
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
                              {task.assignee_ids.length > 3 && (
                                <div className="w-6 h-6 rounded-full bg-muted flex items-center justify-center text-[10px] border-2 border-card">
                                  +{task.assignee_ids.length - 3}
                                </div>
                              )}
                            </div>
                          )}
                        </div>
                      )}
                    </Draggable>
                  ))}
                  {provided.placeholder}
                  {getTasksByStatus(status.id).length === 0 && (
                    <div className="text-center py-8 text-muted-foreground text-sm">
                      No tasks
                    </div>
                  )}
                </div>
              </div>
            )}
          </Droppable>
        ))}
      </div>
    </DragDropContext>
  );
}
