import { useState, useEffect } from "react";
import { useParams, useNavigate, useSearchParams } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { getMyPermissions, hasPermission, Permission } from "../api";
import {
  getProject,
  getProjectMembers,
  updateProject,
} from "../api/projects";
import {
  getTasks,
  createTask,
  updateTask,
  deleteTask,
  addChecklistItem,
  updateChecklistItem,
  deleteChecklistItem,
  generateRecurringTasks,
  getTaskActivity,
  bulkUpdateTasks,
  bulkAssignTasks,
  bulkDeleteTasks,
} from "../api/tasks";
import { getComments, createComment } from "../api/comments";
import {
  BulkTaskActions,
  TaskDetailDialog,
  KanbanBoard,
  TaskListView,
  CreateTaskDialog,
  ProjectSettingsDialog,
} from "../components/tasks";
import { Button } from "../components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../components/ui/tabs";
import { LoadingSpinner } from "../components/ui/loading-spinner";
import { GanttChart } from "../components/GanttChart";
import { DependencyGraph } from "../components/DependencyGraph";
import { toast } from "sonner";
import {
  ArrowLeft,
  Plus,
  CalendarDays,
  Settings,
  Network,
  CalendarClock,
} from "lucide-react";
import { format, isValid } from "date-fns";

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

const DEFAULT_STATUSES = [
  { id: "todo", label: "To Do", color: "#64748b" },
  { id: "in_progress", label: "In Progress", color: "#3b82f6" },
  { id: "review", label: "In Review", color: "#a855f7" },
  { id: "done", label: "Done", color: "#22c55e" },
];

export default function ProjectDetailPage() {
  const { projectId } = useParams();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const [loading, setLoading] = useState(true);
  const [project, setProject] = useState(null);
  const [tasks, setTasks] = useState([]);
  const [projectMembers, setProjectMembers] = useState([]);
  const [viewMode, setViewMode] = useState("kanban");
  const [taskDialogOpen, setTaskDialogOpen] = useState(false);
  const [selectedTask, setSelectedTask] = useState(null);
  const [taskDetailOpen, setTaskDetailOpen] = useState(false);
  const [comments, setComments] = useState([]);
  const [creating, setCreating] = useState(false);
  const [checklist, setChecklist] = useState([]);
  const [activity, setActivity] = useState([]);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [taskStatuses, setTaskStatuses] = useState(DEFAULT_STATUSES);
  const [selectedTaskIds, setSelectedTaskIds] = useState([]);
  const [permissions, setPermissions] = useState([]);

  const canDo = (permission) => hasPermission(permissions, permission);

  useEffect(() => {
    loadData();
  }, [projectId]);

  useEffect(() => {
    const taskIdFromUrl = searchParams.get("task");
    if (taskIdFromUrl && tasks.length > 0) {
      const task = tasks.find((t) => t.task_id === taskIdFromUrl);
      if (task) openTaskDetail(task);
    }
  }, [searchParams, tasks]);

  const loadData = async () => {
    try {
      const [projectData, tasksData, members] = await Promise.all([
        getProject(projectId),
        getTasks(projectId),
        getProjectMembers(projectId),
      ]);
      setProject(projectData);
      setTasks(tasksData);
      setProjectMembers(members);
      // Normalize status objects
      let statuses =
        projectData.task_statuses?.length > 0
          ? projectData.task_statuses.map((s) => ({
              id: s.id,
              label: s.label || s.name || s.id,
              color: s.color || "#6B7280",
            }))
          : DEFAULT_STATUSES;
      setTaskStatuses(statuses);

      if (projectData.org_id) {
        try {
          const permData = await getMyPermissions(projectData.org_id);
          setPermissions(permData.permissions || []);
        } catch (e) {
          console.error("Failed to load permissions:", e);
          setPermissions([]);
        }
      }
    } catch (error) {
      console.error("Failed to load project:", error);
      toast.error("Failed to load project");
    } finally {
      setLoading(false);
    }
  };

  const handleDragEnd = async (result) => {
    const { destination, source, draggableId } = result;
    if (!destination) return;
    if (destination.droppableId === source.droppableId && destination.index === source.index)
      return;

    const newStatus = destination.droppableId;
    const taskId = draggableId;

    // Optimistically update the UI
    const originalTasks = [...tasks];
    setTasks((prev) => prev.map((t) => (t.task_id === taskId ? { ...t, status: newStatus } : t)));

    try {
      await updateTask(taskId, { status: newStatus });
      toast.success("Task moved");
    } catch (error) {
      // Revert optimistic update
      setTasks(originalTasks);
      
      // Check if approval is required (HTTP 428)
      if (error.status === 428 || error.response?.status === 428 || error.message?.toLowerCase().includes("approval")) {
        toast.info("This status change requires approval. Open the task to request approval.");
        const task = originalTasks.find(t => t.task_id === taskId);
        if (task) {
          openTaskDetail(task);
        }
      } else {
        toast.error(error.message || "Failed to move task");
      }
    }
  };

  const handleCreateTask = async (newTask) => {
    if (!newTask.title.trim()) {
      toast.error("Please enter a task title");
      return;
    }

    setCreating(true);
    try {
      const taskData = {
        ...newTask,
        project_id: projectId,
        due_date: newTask.due_date || null,
        start_date: newTask.start_date || null,
      };
      const created = await createTask(taskData);
      setTasks([...tasks, created]);
      setTaskDialogOpen(false);
      toast.success("Task created successfully");
    } catch (error) {
      toast.error(error.message || "Failed to create task");
    } finally {
      setCreating(false);
    }
  };

  const handleUpdateTaskStatus = async (taskId, newStatus) => {
    try {
      await updateTask(taskId, { status: newStatus });
      setTasks(tasks.map((t) => (t.task_id === taskId ? { ...t, status: newStatus } : t)));
      toast.success("Task updated");
    } catch (error) {
      // Check if approval is required (HTTP 428)
      if (error.status === 428 || error.response?.status === 428 || error.message?.toLowerCase().includes("approval")) {
        toast.info("This status change requires approval. Open the task to request approval.");
        // Optionally open the task detail dialog
        const task = tasks.find(t => t.task_id === taskId);
        if (task) {
          openTaskDetail(task);
        }
      } else {
        toast.error(error.message || "Failed to update task");
      }
    }
  };

  const handleDeleteTask = async (taskId) => {
    try {
      await deleteTask(taskId);
      setTasks(tasks.filter((t) => t.task_id !== taskId));
      setTaskDetailOpen(false);
      setSelectedTask(null);
      toast.success("Task deleted");
    } catch {
      toast.error("Failed to delete task");
    }
  };

  const openTaskDetail = async (task) => {
    setSelectedTask(task);
    setChecklist(task.subtasks || task.checklist || []);
    setTaskDetailOpen(true);
    try {
      const [commentsData, activityData] = await Promise.all([
        getComments(task.task_id),
        getTaskActivity(task.task_id),
      ]);
      setComments(commentsData);
      setActivity(activityData);
    } catch (error) {
      console.error("Failed to load task details:", error);
    }
  };

  const handleGenerateRecurring = async (taskId) => {
    try {
      const result = await generateRecurringTasks(taskId, 5);
      toast.success(`Created ${result.created_count} recurring task instances`);
      loadData();
    } catch (error) {
      toast.error(error.message || "Failed to generate recurring tasks");
    }
  };

  const handleUpdateAssignees = async (assigneeIds) => {
    if (!selectedTask) return;
    try {
      await updateTask(selectedTask.task_id, { assignee_ids: assigneeIds });
      setSelectedTask({ ...selectedTask, assignee_ids: assigneeIds });
      setTasks(
        tasks.map((t) =>
          t.task_id === selectedTask.task_id ? { ...t, assignee_ids: assigneeIds } : t
        )
      );
      toast.success("Assignees updated");
    } catch {
      toast.error("Failed to update assignees");
    }
  };

  const handleUpdateDependencies = async (blockedBy, blocks) => {
    if (!selectedTask) return;
    try {
      await updateTask(selectedTask.task_id, { blocked_by: blockedBy, blocks: blocks });
      setSelectedTask({ ...selectedTask, blocked_by: blockedBy, blocks: blocks });
      setTasks(
        tasks.map((t) =>
          t.task_id === selectedTask.task_id
            ? { ...t, blocked_by: blockedBy, blocks: blocks }
            : t
        )
      );
      toast.success("Dependencies updated");
    } catch {
      toast.error("Failed to update dependencies");
    }
  };

  const getTaskById = (taskId) => tasks.find((t) => t.task_id === taskId);

  const handleSaveStatuses = async (newStatuses) => {
    try {
      await updateProject(projectId, { task_statuses: newStatuses });
      setProject({ ...project, task_statuses: newStatuses });
      setTaskStatuses(newStatuses);
      setSettingsOpen(false);
      toast.success("Workflow updated");
    } catch {
      toast.error("Failed to update workflow");
    }
  };

  const handleTaskSelect = (taskId, checked) => {
    if (checked) {
      setSelectedTaskIds([...selectedTaskIds, taskId]);
    } else {
      setSelectedTaskIds(selectedTaskIds.filter((id) => id !== taskId));
    }
  };

  const handleStatusToggle = async (taskId, currentStatus) => {
    const newStatus = currentStatus === "done" ? "todo" : "done";
    await handleUpdateTaskStatus(taskId, newStatus);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-[60vh]">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  if (!project) {
    return (
      <div className="text-center py-12">
        <h2 className="text-xl font-semibold">Project not found</h2>
        <Button variant="outline" className="mt-4" onClick={() => navigate("/projects")}>
          Back to Projects
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-fade-in" data-testid="project-detail-page">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-center gap-4">
          <Button
            variant="ghost"
            size="icon"
            onClick={() => navigate("/projects")}
            data-testid="back-btn"
          >
            <ArrowLeft className="w-5 h-5" />
          </Button>
          <div
            className="w-12 h-12 rounded-lg flex items-center justify-center text-white font-bold text-lg"
            style={{ backgroundColor: project.color }}
          >
            {project.name.charAt(0).toUpperCase()}
          </div>
          <div>
            <h1 className="font-heading text-2xl font-bold tracking-tight">{project.name}</h1>
            <p className="text-muted-foreground">{project.description || "No description"}</p>
            {project.created_at && (
              <p className="text-xs text-muted-foreground mt-1 flex items-center gap-1">
                <CalendarClock className="w-3 h-3" />
                Created {safeFormat(project.created_at, "MMM d, yyyy") || "Unknown"}
                {project.start_date && ` • Started ${safeFormat(project.start_date, "MMM d, yyyy")}`}
                {project.end_date && ` • Due ${safeFormat(project.end_date, "MMM d, yyyy")}`}
              </p>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="icon"
            onClick={() => setSettingsOpen(true)}
            data-testid="project-settings-btn"
          >
            <Settings className="w-4 h-4" />
          </Button>
          {canDo(Permission.TASK_CREATE) && (
            <Button onClick={() => setTaskDialogOpen(true)} data-testid="add-task-btn">
              <Plus className="w-4 h-4 mr-2" />
              Add Task
            </Button>
          )}
        </div>
      </div>

      {/* View Tabs */}
      <Tabs value={viewMode} onValueChange={setViewMode}>
        <TabsList>
          <TabsTrigger value="kanban" data-testid="kanban-tab">
            Kanban
          </TabsTrigger>
          <TabsTrigger value="list" data-testid="list-tab">
            List
          </TabsTrigger>
          <TabsTrigger value="timeline" data-testid="timeline-tab">
            <CalendarDays className="w-4 h-4 mr-1" />
            Timeline
          </TabsTrigger>
          <TabsTrigger value="dependencies" data-testid="dependencies-tab">
            <Network className="w-4 h-4 mr-1" />
            Dependencies
          </TabsTrigger>
        </TabsList>

        <TabsContent value="kanban" className="mt-6">
          <KanbanBoard
            tasks={tasks}
            statuses={taskStatuses}
            members={projectMembers}
            selectedTaskIds={selectedTaskIds}
            canEditTask={canDo(Permission.TASK_EDIT) || canDo(Permission.TASK_CHANGE_STATUS)}
            canDeleteTask={canDo(Permission.TASK_DELETE)}
            onDragEnd={handleDragEnd}
            onTaskClick={openTaskDetail}
            onTaskSelect={handleTaskSelect}
            onStatusChange={handleUpdateTaskStatus}
            onDeleteTask={handleDeleteTask}
          />
        </TabsContent>

        <TabsContent value="list" className="mt-6">
          <TaskListView
            tasks={tasks}
            statuses={taskStatuses}
            members={projectMembers}
            selectedTaskIds={selectedTaskIds}
            onTaskClick={openTaskDetail}
            onTaskSelect={handleTaskSelect}
            onStatusToggle={handleStatusToggle}
            onCreateTask={() => setTaskDialogOpen(true)}
          />
        </TabsContent>

        <TabsContent value="timeline" className="mt-6">
          <GanttChart projectId={projectId} onTaskClick={openTaskDetail} />
        </TabsContent>

        <TabsContent value="dependencies" className="mt-6">
          <DependencyGraph tasks={tasks} taskStatuses={taskStatuses} onTaskClick={openTaskDetail} />
        </TabsContent>
      </Tabs>

      {/* Create Task Dialog */}
      <CreateTaskDialog
        open={taskDialogOpen}
        onOpenChange={setTaskDialogOpen}
        statuses={taskStatuses}
        members={projectMembers}
        creating={creating}
        onSubmit={handleCreateTask}
      />

      {/* Task Detail Dialog */}
      <TaskDetailDialog
        open={taskDetailOpen}
        onOpenChange={setTaskDetailOpen}
        task={selectedTask}
        taskStatuses={taskStatuses}
        members={projectMembers}
        comments={comments}
        activity={activity}
        checklist={checklist}
        currentUserId={user?.user_id}
        canEdit={canDo(Permission.TASK_EDIT) || canDo(Permission.TASK_EDIT_OWN) || canDo(Permission.TASK_CHANGE_STATUS)}
        canDelete={canDo(Permission.TASK_DELETE)}
        canComment={canDo(Permission.COMMENT_CREATE)}
        canApprove={canDo(Permission.WORKFLOW_VIEW) || canDo(Permission.TASK_EDIT)}
        canForceApprove={canDo(Permission.ORG_MANAGE)}
        onUpdateTask={async (taskId, updates) => {
          await updateTask(taskId, updates);
          setSelectedTask((prev) => ({ ...prev, ...updates }));
          setTasks(tasks.map((t) => (t.task_id === taskId ? { ...t, ...updates } : t)));
        }}
        onDeleteTask={handleDeleteTask}
        onGenerateRecurring={handleGenerateRecurring}
        onAddComment={async (content) => {
          const comment = await createComment({ content, task_id: selectedTask.task_id });
          setComments([...comments, comment]);
        }}
        onAddChecklistItem={async (title) => {
          const item = await addChecklistItem(selectedTask.task_id, title);
          const newChecklist = [...checklist, item];
          setChecklist(newChecklist);
          setSelectedTask((prev) => ({ ...prev, subtasks: newChecklist }));
          setTasks(
            tasks.map((t) =>
              t.task_id === selectedTask.task_id ? { ...t, subtasks: newChecklist } : t
            )
          );
        }}
        onToggleChecklistItem={async (itemId, completed) => {
          await updateChecklistItem(selectedTask.task_id, itemId, { completed: !completed });
          const newChecklist = checklist.map((item) =>
            item.item_id === itemId ? { ...item, completed: !completed } : item
          );
          setChecklist(newChecklist);
          setSelectedTask((prev) => ({ ...prev, subtasks: newChecklist }));
          setTasks(
            tasks.map((t) =>
              t.task_id === selectedTask.task_id ? { ...t, subtasks: newChecklist } : t
            )
          );
        }}
        onDeleteChecklistItem={async (itemId) => {
          await deleteChecklistItem(selectedTask.task_id, itemId);
          const newChecklist = checklist.filter((item) => item.item_id !== itemId);
          setChecklist(newChecklist);
          setSelectedTask((prev) => ({ ...prev, subtasks: newChecklist }));
          setTasks(
            tasks.map((t) =>
              t.task_id === selectedTask.task_id ? { ...t, subtasks: newChecklist } : t
            )
          );
        }}
        onUpdateAssignees={handleUpdateAssignees}
        onUpdateDependencies={handleUpdateDependencies}
        onRefreshTask={loadData}
        getTaskById={getTaskById}
      />

      {/* Project Settings Dialog */}
      <ProjectSettingsDialog
        open={settingsOpen}
        onOpenChange={setSettingsOpen}
        projectId={project?.project_id}
        initialStatuses={taskStatuses}
        onSaveStatuses={handleSaveStatuses}
      />

      {/* Bulk Task Actions Toolbar */}
      <BulkTaskActions
        selectedTaskIds={selectedTaskIds}
        tasks={tasks}
        members={projectMembers}
        statuses={taskStatuses}
        onClearSelection={() => setSelectedTaskIds([])}
        onBulkUpdate={async (taskIds, updates) => {
          await bulkUpdateTasks(taskIds, updates);
          loadData();
        }}
        onBulkDelete={async (taskIds) => {
          await bulkDeleteTasks(taskIds);
          setTasks(tasks.filter((t) => !taskIds.includes(t.task_id)));
        }}
        onBulkAssign={async (taskIds, userId) => {
          await bulkAssignTasks(taskIds, userId);
          loadData();
        }}
      />
    </div>
  );
}
