/**
 * TaskDetailDialog - Task detail view with editable fields
 */
import { useState, useEffect, useRef } from "react";
import { Button } from "../ui/button";
import { Input } from "../ui/input";
import { Label } from "../ui/label";
import { Badge } from "../ui/badge";
import { Avatar, AvatarFallback, AvatarImage } from "../ui/avatar";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../ui/tabs";
import { Checkbox } from "../ui/checkbox";
import { Progress } from "../ui/progress";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "../ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../ui/select";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "../ui/dropdown-menu";
import { RichTextEditor, RichTextDisplay } from "../RichTextEditor";
import { FileAttachments } from "../FileAttachments";
import { MentionInput, RenderMentions } from "../MentionInput";
import { TimeTracker } from "../TimeTracker";
import { ApprovalBanner } from "./ApprovalBanner";
import { toast } from "sonner";
import {
  MoreHorizontal,
  Calendar,
  Clock,
  Trash2,
  ListChecks,
  Repeat,
  Users,
  History,
  MessageSquare,
  Paperclip,
  GitBranch,
  ArrowRight,
  AlertTriangle,
  Plus,
  Pencil,
  Check,
  X,
  Lock,
} from "lucide-react";
import { format, formatDistanceToNow, isValid, parseISO } from "date-fns";
import { getTaskApprovalSummary, checkApprovalRequired, requestApproval } from "../../api/workflows";

const PRIORITIES = [
  { id: "low", label: "Low", color: "bg-green-500" },
  { id: "medium", label: "Medium", color: "bg-yellow-500" },
  { id: "high", label: "High", color: "bg-orange-500" },
  { id: "urgent", label: "Urgent", color: "bg-red-500" },
];

const RECURRENCE_OPTIONS = [
  { id: "none", label: "No recurrence" },
  { id: "daily", label: "Daily" },
  { id: "weekly", label: "Weekly" },
  { id: "biweekly", label: "Bi-weekly" },
  { id: "monthly", label: "Monthly" },
  { id: "quarterly", label: "Quarterly" },
  { id: "yearly", label: "Yearly" },
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

const safeFormatDistanceToNow = (dateStr) => {
  if (!dateStr) return null;
  try {
    const date = typeof dateStr === 'string' ? parseISO(dateStr) : dateStr;
    return isValid(date) ? formatDistanceToNow(date, { addSuffix: true }) : null;
  } catch {
    return null;
  }
};

export function TaskDetailDialog({
  open,
  onOpenChange,
  task,
  taskStatuses = [],
  members = [],
  comments = [],
  activity = [],
  checklist = [],
  currentUserId,
  canEdit = true,
  canDelete = true,
  canComment = true,
  canApprove = false,
  canForceApprove = false,
  onUpdateTask,
  onDeleteTask,
  onGenerateRecurring,
  onAddComment,
  onAddChecklistItem,
  onToggleChecklistItem,
  onDeleteChecklistItem,
  onUpdateAssignees,
  onUpdateDependencies,
  onRefreshTask,
  getTaskById,
}) {
  const [activeTab, setActiveTab] = useState("details");
  const [isEditingTitle, setIsEditingTitle] = useState(false);
  const [editedTitle, setEditedTitle] = useState("");
  const [newComment, setNewComment] = useState("");
  const [newChecklistItem, setNewChecklistItem] = useState("");

  // Safety check for task prop
  if (!task) {
    return null;
  }
  const [approvalSummary, setApprovalSummary] = useState(null);
  const [loadingApproval, setLoadingApproval] = useState(false);
  const titleInputRef = useRef(null);

  // Reset editing state when task changes
  useEffect(() => {
    if (task) {
      setEditedTitle(task.title);
      setIsEditingTitle(false);
      loadApprovalSummary();
    }
  }, [task?.task_id]);

  // Load approval summary
  const loadApprovalSummary = async () => {
    if (!task?.task_id) return;
    try {
      setLoadingApproval(true);
      const summary = await getTaskApprovalSummary(task.task_id);
      setApprovalSummary(summary);
    } catch (error) {
      // Silently fail - approval features may not be available
      console.log("Could not load approval summary:", error.message);
    } finally {
      setLoadingApproval(false);
    }
  };

  // Focus input when editing starts
  useEffect(() => {
    if (isEditingTitle && titleInputRef.current) {
      titleInputRef.current.focus();
      titleInputRef.current.select();
    }
  }, [isEditingTitle]);

  if (!task) return null;

  const handleTitleClick = () => {
    if (canEdit) {
      setEditedTitle(task.title);
      setIsEditingTitle(true);
    }
  };

  const handleTitleSave = async () => {
    if (editedTitle.trim() && editedTitle.trim() !== task.title) {
      try {
        await onUpdateTask?.(task.task_id, { title: editedTitle.trim() });
        toast.success("Title updated");
      } catch (error) {
        toast.error("Failed to update title");
        setEditedTitle(task.title);
      }
    }
    setIsEditingTitle(false);
  };

  const handleTitleCancel = () => {
    setEditedTitle(task.title);
    setIsEditingTitle(false);
  };

  const handleTitleKeyDown = (e) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      handleTitleSave();
    } else if (e.key === 'Escape') {
      e.preventDefault();
      e.stopPropagation();
      handleTitleCancel();
    }
  };

  const handleAddComment = async () => {
    if (!newComment.trim()) return;
    try {
      await onAddComment?.(newComment.trim());
      setNewComment("");
    } catch (error) {
      toast.error("Failed to add comment");
    }
  };

  const handleAddChecklistItem = async () => {
    if (!newChecklistItem.trim()) return;
    try {
      await onAddChecklistItem?.(newChecklistItem.trim());
      setNewChecklistItem("");
    } catch (error) {
      toast.error("Failed to add checklist item");
    }
  };

  const getPriorityBadge = (priority) => {
    const p = PRIORITIES.find(pr => pr.id === priority);
    if (!p) return null;
    return (
      <Badge variant="outline" className="flex items-center gap-1">
        <span className={`w-2 h-2 rounded-full ${p.color}`} />
        {p.label}
      </Badge>
    );
  };

  // Handle status change with approval check
  const handleStatusChange = async (newStatus) => {
    if (newStatus === task.status) return;
    
    try {
      // Check if approval is required
      const check = await checkApprovalRequired(task.task_id, newStatus);
      
      if (check.requires_approval) {
        // Request approval instead of direct update
        toast.info("This status change requires approval. Requesting...");
        await requestApproval(task.task_id, newStatus, null);
        toast.success("Approval requested successfully");
        loadApprovalSummary();
        onRefreshTask?.();
        return;
      }
      
      // No approval needed, proceed with update
      await onUpdateTask?.(task.task_id, { status: newStatus });
    } catch (error) {
      // Handle the 428 status code (Precondition Required)
      if (error?.status === 428 || error?.message?.includes("requires approval")) {
        toast.info("Approval required. Requesting...");
        try {
          await requestApproval(task.task_id, newStatus, null);
          toast.success("Approval requested successfully");
          loadApprovalSummary();
          onRefreshTask?.();
        } catch (reqError) {
          toast.error(reqError.message || "Failed to request approval");
        }
      } else {
        toast.error(error.message || "Failed to update status");
      }
    }
  };

  // Handle approval complete (refresh data)
  const handleApprovalComplete = () => {
    loadApprovalSummary();
    onRefreshTask?.();
  };

  const isTaskLocked = approvalSummary?.is_locked || task?.approval_locked;

  const checklistProgress = checklist.length > 0
    ? (checklist.filter(item => item.completed).length / checklist.length) * 100
    : 0;

  const assignees = (task.assignee_ids || [])
    .map(id => members.find(m => m.user_id === id))
    .filter(Boolean);

  const blockedByTasks = (task.blocked_by || [])
    .map(id => getTaskById?.(id))
    .filter(Boolean);

  const blocksTasks = (task.blocks || [])
    .map(id => getTaskById?.(id))
    .filter(Boolean);

  const getActivityIcon = (type) => {
    switch (type) {
      case 'create': return <Plus className="w-4 h-4 text-green-500" />;
      case 'update': return <Pencil className="w-4 h-4 text-blue-500" />;
      case 'comment': return <MessageSquare className="w-4 h-4 text-blue-500" />;
      case 'delete': return <Trash2 className="w-4 h-4 text-red-500" />;
      default: return <History className="w-4 h-4 text-muted-foreground" />;
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent 
        className="max-w-2xl max-h-[90vh] overflow-y-auto"
        onEscapeKeyDown={(e) => {
          if (isEditingTitle) {
            e.preventDefault();
            handleTitleCancel();
          }
        }}
      >
        <DialogHeader>
          <div className="flex items-start justify-between">
            <div className="flex-1 mr-4">
              {/* Editable Title - Click to Edit */}
              {isEditingTitle ? (
                <div className="flex items-center gap-2">
                  <Input
                    ref={titleInputRef}
                    value={editedTitle}
                    onChange={(e) => setEditedTitle(e.target.value)}
                    onBlur={handleTitleSave}
                    onKeyDown={handleTitleKeyDown}
                    className="text-lg font-semibold h-auto py-1"
                    placeholder="Task title..."
                    data-testid="task-title-edit-input"
                  />
                  <Button size="icon" variant="ghost" className="h-8 w-8" onClick={handleTitleSave}>
                    <Check className="w-4 h-4 text-green-500" />
                  </Button>
                  <Button size="icon" variant="ghost" className="h-8 w-8" onClick={handleTitleCancel}>
                    <X className="w-4 h-4 text-muted-foreground" />
                  </Button>
                </div>
              ) : (
                <DialogTitle 
                  className={`text-lg font-semibold ${!isTaskLocked && canEdit ? 'cursor-pointer hover:bg-accent/50' : ''} rounded px-2 py-1 -mx-2 flex items-center gap-2 group`}
                  onClick={isTaskLocked ? undefined : handleTitleClick}
                  data-testid="task-title-display"
                >
                  {isTaskLocked && <Lock className="w-4 h-4 text-amber-500" />}
                  {task?.title || "Untitled Task"}
                  {canEdit && !isTaskLocked && (
                    <Pencil className="w-4 h-4 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
                  )}
                </DialogTitle>
              )}
              <div className="flex items-center gap-2 mt-1">
                {task.recurrence && task.recurrence !== "none" && (
                  <Badge variant="outline">
                    <Repeat className="w-3 h-3 mr-1" />
                    {task.recurrence}
                  </Badge>
                )}
                {isTaskLocked && (
                  <Badge variant="outline" className="border-amber-400 text-amber-600">
                    <Lock className="w-3 h-3 mr-1" />
                    Locked
                  </Badge>
                )}
              </div>
            </div>
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" size="icon">
                  <MoreHorizontal className="w-4 h-4" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                {task.recurrence && task.recurrence !== "none" && canEdit && !isTaskLocked && (
                  <>
                    <DropdownMenuItem onClick={() => onGenerateRecurring?.(task.task_id)}>
                      <Repeat className="w-4 h-4 mr-2" />
                      Generate Recurring
                    </DropdownMenuItem>
                    <DropdownMenuSeparator />
                  </>
                )}
                {canDelete && !isTaskLocked && (
                  <DropdownMenuItem 
                    className="text-destructive" 
                    onClick={() => onDeleteTask?.(task.task_id)}
                  >
                    <Trash2 className="w-4 h-4 mr-2" />
                    Delete Task
                  </DropdownMenuItem>
                )}
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </DialogHeader>

        {/* Approval Banner */}
        <ApprovalBanner
          approvalSummary={approvalSummary}
          taskId={task.task_id}
          currentUserId={currentUserId}
          canApprove={canApprove}
          canForceApprove={canForceApprove}
          onApprovalComplete={handleApprovalComplete}
        />

        <Tabs value={activeTab} onValueChange={setActiveTab} className="mt-4">
          <TabsList className="w-full">
            <TabsTrigger value="details" className="flex-1">Details</TabsTrigger>
            <TabsTrigger value="activity" className="flex-1">
              <History className="w-4 h-4 mr-1" />
              Activity
            </TabsTrigger>
          </TabsList>

          <TabsContent value="details" className="space-y-6 pt-4">
            {/* Status & Priority */}
            <div className="flex items-center gap-4 flex-wrap">
              {canEdit ? (
                <Select 
                  value={task.status} 
                  onValueChange={handleStatusChange}
                  disabled={isTaskLocked}
                >
                  <SelectTrigger className="w-[140px]" data-testid="task-status-select">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {taskStatuses.map((s) => (
                      <SelectItem key={s.id} value={s.id}>
                        <div className="flex items-center gap-2">
                          {s.label}
                          {approvalSummary?.requires_approval_for_status?.includes(s.id) && (
                            <Lock className="w-3 h-3 text-amber-500" />
                          )}
                        </div>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              ) : (
                <div 
                  className="flex items-center gap-2 px-3 py-2 rounded-md border border-destructive/50 bg-destructive/5 cursor-not-allowed"
                  data-testid="task-status-readonly"
                >
                  <Badge variant="outline" className="text-destructive border-destructive/50">
                    {taskStatuses.find(s => s.id === task.status)?.label || task.status}
                  </Badge>
                  <span className="text-xs text-destructive font-medium">You don&apos;t have Privilege</span>
                </div>
              )}
              {getPriorityBadge(task.priority)}
            </div>

            {/* Start Date & Due Date */}
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label className="text-sm font-medium flex items-center gap-2">
                  <Calendar className="w-4 h-4" />
                  Start Date <span className="text-destructive">*</span>
                </Label>
                {canEdit && !isTaskLocked ? (
                  <Input
                    type="date"
                    value={task.start_date ? task.start_date.split('T')[0] : ''}
                    onChange={(e) => onUpdateTask?.(task.task_id, { start_date: e.target.value })}
                    data-testid="task-edit-start-date"
                  />
                ) : (
                  <div className="text-sm text-muted-foreground py-2">
                    {safeFormat(task.start_date, "MMM d, yyyy") || "Not set"}
                  </div>
                )}
              </div>
              <div className="space-y-2">
                <Label className="text-sm font-medium flex items-center gap-2">
                  <Calendar className="w-4 h-4" />
                  Due Date <span className="text-destructive">*</span>
                </Label>
                {canEdit && !isTaskLocked ? (
                  <Input
                    type="date"
                    value={task.due_date ? task.due_date.split('T')[0] : ''}
                    min={task.start_date ? task.start_date.split('T')[0] : ''}
                    onChange={(e) => {
                      const startDate = task.start_date ? task.start_date.split('T')[0] : '';
                      if (startDate && e.target.value < startDate) {
                        toast.error("Due date must be after or equal to start date");
                        return;
                      }
                      onUpdateTask?.(task.task_id, { due_date: e.target.value });
                    }}
                    data-testid="task-edit-due-date"
                  />
                ) : (
                  <div className="text-sm text-muted-foreground py-2">
                    {safeFormat(task.due_date, "MMM d, yyyy") || "Not set"}
                  </div>
                )}
              </div>
            </div>

            {/* Recurrence */}
            <div className="space-y-2">
              <Label className="text-sm font-medium flex items-center gap-2">
                <Repeat className="w-4 h-4" />
                Recurrence
              </Label>
              <Select 
                value={task.recurrence || "none"} 
                onValueChange={(value) => onUpdateTask?.(task.task_id, { recurrence: value })}
                disabled={!canEdit}
              >
                <SelectTrigger className="w-[180px]" data-testid="recurrence-select">
                  <SelectValue placeholder="No recurrence" />
                </SelectTrigger>
                <SelectContent>
                  {RECURRENCE_OPTIONS.map((option) => (
                    <SelectItem key={option.id} value={option.id}>
                      {option.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {task.recurrence && task.recurrence !== "none" && (
                <p className="text-xs text-muted-foreground">
                  This task will repeat {task.recurrence}. Use the menu to generate recurring instances.
                </p>
              )}
            </div>

            {/* Description */}
            <div className="space-y-2">
              <Label className="text-sm font-medium">Description</Label>
              {canEdit ? (
                <RichTextEditor
                  content={task.description || ""}
                  onChange={(content) => onUpdateTask?.(task.task_id, { description: content })}
                  placeholder="Add a description..."
                />
              ) : (
                <RichTextDisplay content={task.description || "No description"} />
              )}
            </div>

            {/* Assignees */}
            <div className="space-y-2">
              <Label className="text-sm font-medium flex items-center gap-2">
                <Users className="w-4 h-4" />
                Assignees
              </Label>
              <div className="flex flex-wrap gap-2">
                {assignees.map((member) => (
                  <Badge key={member.user_id} variant="secondary" className="flex items-center gap-1">
                    <Avatar className="w-4 h-4">
                      <AvatarImage src={member.picture} />
                      <AvatarFallback className="text-[8px]">{member.name?.charAt(0)}</AvatarFallback>
                    </Avatar>
                    {member.name}
                    {canEdit && (
                      <X 
                        className="w-3 h-3 ml-1 cursor-pointer hover:text-destructive" 
                        onClick={() => {
                          const newAssignees = task.assignee_ids.filter(id => id !== member.user_id);
                          onUpdateAssignees?.(newAssignees);
                        }}
                      />
                    )}
                  </Badge>
                ))}
                {canEdit && (
                  <Select onValueChange={(value) => {
                    if (!task.assignee_ids?.includes(value)) {
                      onUpdateAssignees?.([...(task.assignee_ids || []), value]);
                    }
                  }}>
                    <SelectTrigger className="w-[140px] h-8">
                      <Plus className="w-4 h-4 mr-1" />
                      Add
                    </SelectTrigger>
                    <SelectContent>
                      {members.filter(m => !task.assignee_ids?.includes(m.user_id)).map((m) => (
                        <SelectItem key={m.user_id} value={m.user_id}>
                          <div className="flex items-center gap-2">
                            <Avatar className="w-5 h-5">
                              <AvatarImage src={m.picture} />
                              <AvatarFallback className="text-[10px]">{m.name?.charAt(0)}</AvatarFallback>
                            </Avatar>
                            {m.name}
                          </div>
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                )}
              </div>
            </div>

            {/* Checklist */}
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <Label className="text-sm font-medium flex items-center gap-2">
                  <ListChecks className="w-4 h-4" />
                  Checklist
                  {checklist.length > 0 && (
                    <span className="text-muted-foreground">
                      ({checklist.filter(i => i.completed).length}/{checklist.length})
                    </span>
                  )}
                </Label>
              </div>
              {checklist.length > 0 && (
                <Progress value={checklistProgress} className="h-2" />
              )}
              <div className="space-y-2">
                {checklist.map((item) => (
                  <div key={item.item_id} className="flex items-center gap-2 group">
                    <Checkbox
                      checked={item.completed}
                      onCheckedChange={(checked) => onToggleChecklistItem?.(item.item_id, item.completed)}
                      disabled={!canEdit}
                    />
                    <span className={`flex-1 text-sm ${item.completed ? 'line-through text-muted-foreground' : ''}`}>
                      {item.title}
                    </span>
                    {canEdit && (
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-6 w-6 opacity-0 group-hover:opacity-100"
                        onClick={() => onDeleteChecklistItem?.(item.item_id)}
                      >
                        <Trash2 className="w-3 h-3 text-destructive" />
                      </Button>
                    )}
                  </div>
                ))}
              </div>
              {canEdit && (
                <div className="flex gap-2">
                  <Input
                    placeholder="Add checklist item..."
                    value={newChecklistItem}
                    onChange={(e) => setNewChecklistItem(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && handleAddChecklistItem()}
                    className="h-8 text-sm"
                  />
                  <Button size="sm" variant="outline" onClick={handleAddChecklistItem} disabled={!newChecklistItem.trim()}>
                    <Plus className="w-4 h-4" />
                  </Button>
                </div>
              )}
            </div>

            {/* Dependencies */}
            {(blockedByTasks.length > 0 || blocksTasks.length > 0) && (
              <div className="space-y-2">
                <Label className="text-sm font-medium flex items-center gap-2">
                  <GitBranch className="w-4 h-4" />
                  Dependencies
                </Label>
                {blockedByTasks.length > 0 && (
                  <div className="space-y-1">
                    <span className="text-xs text-muted-foreground flex items-center gap-1">
                      <AlertTriangle className="w-3 h-3" />
                      Blocked by:
                    </span>
                    <div className="flex flex-wrap gap-1">
                      {blockedByTasks.map((t) => (
                        <Badge key={t.task_id} variant="outline" className="text-xs">
                          {t.title}
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}
                {blocksTasks.length > 0 && (
                  <div className="space-y-1">
                    <span className="text-xs text-muted-foreground flex items-center gap-1">
                      <ArrowRight className="w-3 h-3" />
                      Blocks:
                    </span>
                    <div className="flex flex-wrap gap-1">
                      {blocksTasks.map((t) => (
                        <Badge key={t.task_id} variant="outline" className="text-xs">
                          {t.title}
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Time Tracking */}
            <div className="space-y-2">
              <Label className="text-sm font-medium flex items-center gap-2">
                <Clock className="w-4 h-4" />
                Time Tracking
              </Label>
              <TimeTracker taskId={task.task_id} estimatedHours={task.estimated_hours} />
            </div>

            {/* Attachments */}
            <div className="space-y-2">
              <FileAttachments taskId={task.task_id} canEdit={canEdit} />
            </div>

            {/* Comments */}
            <div className="space-y-3">
              <Label className="text-sm font-medium flex items-center gap-2">
                <MessageSquare className="w-4 h-4" />
                Comments ({comments.length})
              </Label>
              <div className="space-y-3 max-h-[200px] overflow-y-auto">
                {comments.map((comment) => (
                  <div key={comment.comment_id} className="flex gap-3">
                    <Avatar className="w-8 h-8">
                      <AvatarImage src={comment.author_picture} />
                      <AvatarFallback>{comment.author_name?.charAt(0)}</AvatarFallback>
                    </Avatar>
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <span className="font-medium text-sm">{comment.author_name}</span>
                        <span className="text-xs text-muted-foreground">
                          {safeFormatDistanceToNow(comment.created_at) || "recently"}
                        </span>
                      </div>
                      <div className="text-sm text-muted-foreground mt-1">
                        <RenderMentions text={comment.content} members={members} />
                      </div>
                    </div>
                  </div>
                ))}
                {comments.length === 0 && (
                  <p className="text-sm text-muted-foreground text-center py-2">No comments yet</p>
                )}
              </div>
              {canComment && (
                <div className="flex gap-2 pt-2 border-t">
                  <MentionInput
                    value={newComment}
                    onChange={setNewComment}
                    onSubmit={handleAddComment}
                    members={members}
                    placeholder="Add a comment... Use @ to mention"
                  />
                  <Button size="icon" onClick={handleAddComment} disabled={!newComment.trim()}>
                    <MessageSquare className="w-4 h-4" />
                  </Button>
                </div>
              )}
            </div>
          </TabsContent>

          <TabsContent value="activity" className="space-y-4 pt-4">
            <div className="space-y-3">
              {activity.map((item, index) => (
                <div key={index} className="flex gap-3 items-start">
                  <div className="mt-0.5">{getActivityIcon(item.type)}</div>
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-sm">{item.user_name}</span>
                      <span className="text-xs text-muted-foreground">
                        {safeFormatDistanceToNow(item.created_at) || "recently"}
                      </span>
                    </div>
                    <p className="text-sm text-muted-foreground">
                      {item.action} {item.resource_type}
                      {item.details && typeof item.details === 'object' && Object.keys(item.details).length > 0 && (
                        <span className="text-xs ml-1">
                          ({Object.entries(item.details).map(([k, v]) => `${k}: ${v}`).join(', ')})
                        </span>
                      )}
                    </p>
                  </div>
                </div>
              ))}
              {activity.length === 0 && (
                <p className="text-sm text-muted-foreground text-center py-4">No activity yet</p>
              )}
            </div>
          </TabsContent>
        </Tabs>
      </DialogContent>
    </Dialog>
  );
}