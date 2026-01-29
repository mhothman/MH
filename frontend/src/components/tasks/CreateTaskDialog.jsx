/**
 * CreateTaskDialog - Modal for creating a new task
 */
import { useState } from "react";
import { format, addDays } from "date-fns";
import { Button } from "../ui/button";
import { Input } from "../ui/input";
import { Label } from "../ui/label";
import { Avatar, AvatarFallback, AvatarImage } from "../ui/avatar";
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
import { LoadingSpinner } from "../ui/loading-spinner";
import { RichTextEditor } from "../RichTextEditor";
import { Users, Repeat, Calendar } from "lucide-react";
import { toast } from "sonner";

const PRIORITIES = [
  { id: "low", label: "Low", color: "bg-green-500" },
  { id: "medium", label: "Medium", color: "bg-yellow-500" },
  { id: "high", label: "High", color: "bg-orange-500" },
  { id: "urgent", label: "Urgent", color: "bg-red-500" },
];

const DEFAULT_STATUSES = [
  { id: "todo", label: "To Do", color: "#64748b" },
  { id: "in_progress", label: "In Progress", color: "#3b82f6" },
  { id: "review", label: "In Review", color: "#a855f7" },
  { id: "done", label: "Done", color: "#22c55e" },
];

// Helper function to get default dates
const getDefaultDates = () => ({
  start_date: format(new Date(), "yyyy-MM-dd"),
  due_date: format(addDays(new Date(), 10), "yyyy-MM-dd"),
});

export function CreateTaskDialog({
  open,
  onOpenChange,
  statuses = DEFAULT_STATUSES,
  members = [],
  creating = false,
  onSubmit,
}) {
  const [newTask, setNewTask] = useState({
    title: "",
    description: "",
    status: statuses.length > 0 ? statuses[0].id : "todo",
    priority: "medium",
    ...getDefaultDates(),
    recurrence: "none",
    assignee_ids: [],
  });

  const handleSubmit = async () => {
    // Validate required fields
    if (!newTask.title.trim()) {
      toast.error("Please enter a task title");
      return;
    }
    
    if (!newTask.start_date) {
      toast.error("Please select a start date");
      return;
    }
    
    if (!newTask.due_date) {
      toast.error("Please select a due date");
      return;
    }
    
    // Validate end date is after start date
    if (new Date(newTask.due_date) < new Date(newTask.start_date)) {
      toast.error("Due date must be after or equal to start date");
      return;
    }
    
    await onSubmit(newTask);
    // Reset form
    setNewTask({
      title: "",
      description: "",
      status: statuses.length > 0 ? statuses[0].id : "todo",
      priority: "medium",
      ...getDefaultDates(),
      recurrence: "none",
      assignee_ids: [],
    });
  };

  const handleOpenChange = (isOpen) => {
    if (!isOpen) {
      setNewTask({
        title: "",
        description: "",
        status: statuses.length > 0 ? statuses[0].id : "todo",
        priority: "medium",
        ...getDefaultDates(),
        recurrence: "none",
        assignee_ids: [],
      });
    }
    onOpenChange(isOpen);
  };

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Create New Task</DialogTitle>
        </DialogHeader>
        <div className="space-y-4 pt-4">
          <div className="space-y-2">
            <Label>Title</Label>
            <Input
              placeholder="Enter task title"
              value={newTask.title}
              onChange={(e) => setNewTask({ ...newTask, title: e.target.value })}
              data-testid="task-title-input"
            />
          </div>
          <div className="space-y-2">
            <Label>Description</Label>
            <RichTextEditor
              content={newTask.description}
              onChange={(html) => setNewTask({ ...newTask, description: html })}
              placeholder="Enter task description (optional)"
            />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>Priority</Label>
              <Select
                value={newTask.priority}
                onValueChange={(value) => setNewTask({ ...newTask, priority: value })}
              >
                <SelectTrigger data-testid="task-priority-select">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {PRIORITIES.map((p) => (
                    <SelectItem key={p.id} value={p.id}>
                      <div className="flex items-center gap-2">
                        <span className={`w-2 h-2 rounded-full ${p.color}`} />
                        {p.label}
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Status</Label>
              <Select
                value={newTask.status}
                onValueChange={(value) => setNewTask({ ...newTask, status: value })}
              >
                <SelectTrigger data-testid="task-status-select">
                  <SelectValue placeholder="Select status" />
                </SelectTrigger>
                <SelectContent>
                  {(statuses.length > 0 ? statuses : DEFAULT_STATUSES).map((s) => (
                    <SelectItem key={s.id} value={s.id}>
                      {s.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
          <div className="space-y-2">
            <Label className="flex items-center gap-2">
              <Users className="w-4 h-4" />
              Assignees
            </Label>
            <Select
              value={newTask.assignee_ids[0] || "unassigned"}
              onValueChange={(value) =>
                setNewTask({
                  ...newTask,
                  assignee_ids: value && value !== "unassigned" ? [value] : [],
                })
              }
            >
              <SelectTrigger>
                <SelectValue placeholder="Select assignee" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="unassigned">Unassigned</SelectItem>
                {members.map((m) => (
                  <SelectItem key={m.user_id} value={m.user_id}>
                    <div className="flex items-center gap-2">
                      <Avatar className="w-5 h-5">
                        <AvatarImage src={m.picture} />
                        <AvatarFallback className="text-[10px]">
                          {m.name?.charAt(0)}
                        </AvatarFallback>
                      </Avatar>
                      {m.name}
                    </div>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>Start Date</Label>
              <Input
                type="date"
                value={newTask.start_date}
                onChange={(e) => setNewTask({ ...newTask, start_date: e.target.value })}
              />
            </div>
            <div className="space-y-2">
              <Label>Due Date</Label>
              <Input
                type="date"
                value={newTask.due_date}
                onChange={(e) => setNewTask({ ...newTask, due_date: e.target.value })}
              />
            </div>
          </div>
          <div className="space-y-2">
            <Label className="flex items-center gap-2">
              <Repeat className="w-4 h-4" />
              Recurrence
            </Label>
            <Select
              value={newTask.recurrence}
              onValueChange={(value) => setNewTask({ ...newTask, recurrence: value })}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="none">No recurrence</SelectItem>
                <SelectItem value="daily">Daily</SelectItem>
                <SelectItem value="weekly">Weekly</SelectItem>
                <SelectItem value="monthly">Monthly</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="flex justify-end gap-2 pt-4">
            <Button variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button onClick={handleSubmit} disabled={creating} data-testid="submit-task-btn">
              {creating ? <LoadingSpinner size="sm" /> : "Create Task"}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
