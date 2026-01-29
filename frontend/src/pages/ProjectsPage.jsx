import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { getOrganizations, getMyPermissions, hasPermission, Permission } from "../api";
import { getProjects, createProject, updateProject, deleteProject } from "../api/projects";
import { getCustomers } from "../api/customers";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Textarea } from "../components/ui/textarea";
import { Card, CardContent } from "../components/ui/card";
import { Badge } from "../components/ui/badge";
import { Progress } from "../components/ui/progress";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "../components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../components/ui/select";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "../components/ui/dropdown-menu";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "../components/ui/alert-dialog";
import { LoadingSpinner } from "../components/ui/loading-spinner";
import { toast } from "sonner";
import {
  Plus,
  FolderKanban,
  Search,
  LayoutGrid,
  List,
  Calendar,
  Users,
  MoreHorizontal,
  Building2,
  Pencil,
  Trash2,
} from "lucide-react";
import { format } from "date-fns";
import { useAppData } from "../context/AppDataContext";

export default function ProjectsPage() {
  const navigate = useNavigate();
  const { 
    projects: globalProjects, 
    organizations, 
    customers: globalCustomers,
    permissions: globalPermissions,
    currentOrgId,
    loadProjects,
    loadCustomers,
    setProjects: setGlobalProjects,
    projectsLoading 
  } = useAppData();
  
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [viewMode, setViewMode] = useState("grid");
  const [statusFilter, setStatusFilter] = useState("all");
  const [dialogOpen, setDialogOpen] = useState(false);
  const [creating, setCreating] = useState(false);
  const [editingProject, setEditingProject] = useState(null);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [projectToDelete, setProjectToDelete] = useState(null);
  const [newProject, setNewProject] = useState({
    name: "",
    description: "",
    status: "planned",
    color: "#3B82F6",
    customer_id: "none",
  });
  
  // Use global data
  const projects = globalProjects;
  const customers = globalCustomers;
  const permissions = globalPermissions;
  
  // Permission check helper
  const canDo = (permission) => hasPermission(permissions, permission);

  useEffect(() => {
    let isMounted = true;
    
    const loadData = async () => {
      try {
        // Load from global context
        await Promise.all([
          loadProjects(),
          currentOrgId ? loadCustomers(currentOrgId) : Promise.resolve(),
        ]);
        
        if (!isMounted) return;
      } catch (error) {
        if (!isMounted) return;
        console.error("Failed to load projects:", error);
      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    };
    
    loadData();
    
    return () => {
      isMounted = false;
    };
  }, []);

  const handleCreateProject = async () => {
    if (!newProject.name.trim()) {
      toast.error("Please enter a project name");
      return;
    }

    if (organizations.length === 0) {
      toast.error("No organization found");
      return;
    }

    setCreating(true);
    try {
      const projectData = {
        name: newProject.name,
        description: newProject.description || null,
        status: newProject.status,
        color: newProject.color,
      };
      
      // Only include customer_id if it's actually selected
      if (newProject.customer_id && newProject.customer_id !== "" && newProject.customer_id !== "none") {
        projectData.customer_id = newProject.customer_id;
      }
      
      const created = await createProject(organizations[0].org_id, projectData);
      setProjects([created, ...projects]);
      setDialogOpen(false);
      setNewProject({ name: "", description: "", status: "planned", color: "#3B82F6", customer_id: "none" });
      toast.success("Project created successfully");
      navigate(`/projects/${created.project_id}`);
    } catch (error) {
      toast.error(error.message || "Failed to create project");
    } finally {
      setCreating(false);
    }
  };

  const handleOpenEditDialog = (project, e) => {
    e.stopPropagation();
    setEditingProject(project);
    setNewProject({
      name: project.name || "",
      description: project.description || "",
      status: project.status || "planned",
      color: project.color || "#3B82F6",
      customer_id: project.customer_id || "none",
    });
    setDialogOpen(true);
  };

  const handleUpdateProject = async () => {
    if (!newProject.name.trim()) {
      toast.error("Please enter a project name");
      return;
    }

    setCreating(true);
    try {
      const projectData = {
        name: newProject.name,
        description: newProject.description || null,
        status: newProject.status,
        color: newProject.color,
      };
      
      if (newProject.customer_id && newProject.customer_id !== "" && newProject.customer_id !== "none") {
        projectData.customer_id = newProject.customer_id;
      } else {
        projectData.customer_id = null;
      }
      
      await updateProject(editingProject.project_id, projectData);
      setProjects(projects.map(p => 
        p.project_id === editingProject.project_id 
          ? { ...p, ...projectData }
          : p
      ));
      setDialogOpen(false);
      setEditingProject(null);
      setNewProject({ name: "", description: "", status: "planned", color: "#3B82F6", customer_id: "none" });
      toast.success("Project updated successfully");
    } catch (error) {
      toast.error(error.message || "Failed to update project");
    } finally {
      setCreating(false);
    }
  };

  const handleDeleteProject = async () => {
    if (!projectToDelete) return;
    
    try {
      await deleteProject(projectToDelete.project_id);
      setProjects(projects.filter(p => p.project_id !== projectToDelete.project_id));
      setDeleteDialogOpen(false);
      setProjectToDelete(null);
      toast.success("Project deleted successfully");
    } catch (error) {
      toast.error(error.message || "Failed to delete project");
    }
  };

  const handleCloseDialog = () => {
    setDialogOpen(false);
    setEditingProject(null);
    setNewProject({ name: "", description: "", status: "planned", color: "#3B82F6", customer_id: "none" });
  };

  const handleDialogOpenChange = (open) => {
    if (open) {
      setDialogOpen(true);
    } else {
      handleCloseDialog();
    }
  };

  const filteredProjects = projects.filter((project) => {
    const matchesSearch = project.name.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesStatus = statusFilter === "all" || project.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  const getStatusBadge = (status) => {
    const variants = {
      planned: "secondary",
      active: "default",
      on_hold: "outline",
      completed: "default",
      archived: "secondary",
    };
    const labels = {
      planned: "Planned",
      active: "Active",
      on_hold: "On Hold",
      completed: "Completed",
      archived: "Archived",
    };
    return (
      <Badge variant={variants[status] || "secondary"}>
        {labels[status] || status}
      </Badge>
    );
  };

  const colorOptions = [
    "#3B82F6", "#10B981", "#F59E0B", "#EF4444", "#8B5CF6",
    "#EC4899", "#06B6D4", "#84CC16", "#F97316", "#6366F1",
  ];

  if (loading) {
    return (
      <div className="flex items-center justify-center h-[60vh]">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-fade-in" data-testid="projects-page">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="font-heading text-2xl sm:text-3xl font-bold tracking-tight">
            Projects
          </h1>
          <p className="text-muted-foreground mt-1">
            Manage and organize your team's projects
          </p>
        </div>
        
        <Dialog open={dialogOpen} onOpenChange={handleDialogOpenChange}>
          {canDo(Permission.PROJECT_CREATE) && (
            <DialogTrigger asChild>
              <Button data-testid="create-project-btn">
                <Plus className="w-4 h-4 mr-2" />
                New Project
              </Button>
            </DialogTrigger>
          )}
          <DialogContent>
            <DialogHeader>
              <DialogTitle>{editingProject ? "Edit Project" : "Create New Project"}</DialogTitle>
            </DialogHeader>
            <div className="space-y-4 pt-4">
              <div className="space-y-2">
                <Label htmlFor="project-name">Project Name</Label>
                <Input
                  id="project-name"
                  placeholder="Enter project name"
                  value={newProject.name}
                  onChange={(e) => setNewProject({ ...newProject, name: e.target.value })}
                  data-testid="project-name-input"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="project-description">Description</Label>
                <Textarea
                  id="project-description"
                  placeholder="Enter project description (optional)"
                  value={newProject.description}
                  onChange={(e) => setNewProject({ ...newProject, description: e.target.value })}
                  data-testid="project-description-input"
                />
              </div>

              <div className="space-y-2">
                <Label>Status</Label>
                <Select
                  value={newProject.status}
                  onValueChange={(value) => setNewProject({ ...newProject, status: value })}
                >
                  <SelectTrigger data-testid="project-status-select">
                    <SelectValue placeholder="Select status" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="planned">Planned</SelectItem>
                    <SelectItem value="active">Active</SelectItem>
                    <SelectItem value="on_hold">On Hold</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label className="flex items-center gap-2">
                  <Building2 className="w-4 h-4" />
                  Customer
                </Label>
                <Select
                  value={newProject.customer_id}
                  onValueChange={(value) => setNewProject({ ...newProject, customer_id: value })}
                >
                  <SelectTrigger data-testid="project-customer-select">
                    <SelectValue placeholder="Select customer (optional)" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="none">No customer</SelectItem>
                    {customers.map((customer) => (
                      <SelectItem key={customer.customer_id} value={customer.customer_id}>
                        <div className="flex items-center gap-2">
                          <Users className="w-4 h-4" />
                          {customer.name}
                          {customer.company && <span className="text-muted-foreground text-xs">({customer.company})</span>}
                        </div>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label>Color</Label>
                <div className="flex flex-wrap gap-2">
                  {colorOptions.map((color) => (
                    <button
                      key={color}
                      type="button"
                      className={`w-8 h-8 rounded-md transition-all ${
                        newProject.color === color ? "ring-2 ring-offset-2 ring-primary" : ""
                      }`}
                      style={{ backgroundColor: color }}
                      onClick={() => setNewProject({ ...newProject, color })}
                    />
                  ))}
                </div>
              </div>

              <div className="flex justify-end gap-2 pt-4">
                <Button variant="outline" onClick={handleCloseDialog}>
                  Cancel
                </Button>
                <Button onClick={editingProject ? handleUpdateProject : handleCreateProject} disabled={creating} data-testid="submit-project-btn">
                  {creating ? <LoadingSpinner size="sm" /> : (editingProject ? "Update Project" : "Create Project")}
                </Button>
              </div>
            </div>
          </DialogContent>
        </Dialog>
      </div>

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <Input
            placeholder="Search projects..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-10"
            data-testid="search-projects-input"
          />
        </div>
        
        <Select value={statusFilter} onValueChange={setStatusFilter}>
          <SelectTrigger className="w-[150px]" data-testid="status-filter">
            <SelectValue placeholder="All Status" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Status</SelectItem>
            <SelectItem value="planned">Planned</SelectItem>
            <SelectItem value="active">Active</SelectItem>
            <SelectItem value="on_hold">On Hold</SelectItem>
            <SelectItem value="completed">Completed</SelectItem>
          </SelectContent>
        </Select>

        <div className="flex border border-border rounded-md">
          <Button
            variant={viewMode === "grid" ? "secondary" : "ghost"}
            size="icon"
            onClick={() => setViewMode("grid")}
            data-testid="grid-view-btn"
          >
            <LayoutGrid className="w-4 h-4" />
          </Button>
          <Button
            variant={viewMode === "list" ? "secondary" : "ghost"}
            size="icon"
            onClick={() => setViewMode("list")}
            data-testid="list-view-btn"
          >
            <List className="w-4 h-4" />
          </Button>
        </div>
      </div>

      {/* Projects Grid/List */}
      {filteredProjects.length === 0 ? (
        <Card>
          <CardContent className="py-12">
            <div className="empty-state">
              <FolderKanban className="empty-state-icon" />
              <h3 className="font-medium text-lg mt-4">No projects found</h3>
              <p className="text-muted-foreground mt-1">
                {searchQuery || statusFilter !== "all"
                  ? "Try adjusting your filters"
                  : "Create your first project to get started"}
              </p>
              {!searchQuery && statusFilter === "all" && (
                <Button className="mt-4" onClick={() => setDialogOpen(true)}>
                  <Plus className="w-4 h-4 mr-2" />
                  Create Project
                </Button>
              )}
            </div>
          </CardContent>
        </Card>
      ) : viewMode === "grid" ? (
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredProjects.map((project) => (
            <Card
              key={project.project_id}
              className="project-card"
              onClick={() => navigate(`/projects/${project.project_id}`)}
              data-testid={`project-card-${project.project_id}`}
            >
              <CardContent className="p-0">
                <div
                  className="h-2 w-full rounded-t-lg"
                  style={{ backgroundColor: project.color }}
                />
                <div className="p-4">
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex items-center gap-3">
                      <div
                        className="w-10 h-10 rounded-md flex items-center justify-center text-white font-semibold"
                        style={{ backgroundColor: project.color }}
                      >
                        {project.name.charAt(0).toUpperCase()}
                      </div>
                      <div>
                        <h3 className="font-semibold truncate max-w-[180px]">{project.name}</h3>
                        {getStatusBadge(project.status)}
                      </div>
                    </div>
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild onClick={(e) => e.stopPropagation()}>
                        <Button variant="ghost" size="icon" className="h-8 w-8" data-testid={`project-menu-${project.project_id}`}>
                          <MoreHorizontal className="w-4 h-4" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end" onClick={(e) => e.stopPropagation()}>
                        {canDo(Permission.PROJECT_EDIT) && (
                          <DropdownMenuItem onClick={(e) => handleOpenEditDialog(project, e)} data-testid={`edit-project-${project.project_id}`}>
                            <Pencil className="w-4 h-4 mr-2" />
                            Edit
                          </DropdownMenuItem>
                        )}
                        {canDo(Permission.PROJECT_DELETE) && (
                          <>
                            <DropdownMenuSeparator />
                            <DropdownMenuItem 
                              className="text-destructive focus:text-destructive"
                              onClick={(e) => {
                                e.stopPropagation();
                                setProjectToDelete(project);
                                setDeleteDialogOpen(true);
                              }}
                              data-testid={`delete-project-${project.project_id}`}
                            >
                              <Trash2 className="w-4 h-4 mr-2" />
                              Delete
                            </DropdownMenuItem>
                          </>
                        )}
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </div>

                  {project.description && (
                    <p className="text-sm text-muted-foreground line-clamp-2 mb-4">
                      {project.description}
                    </p>
                  )}

                  <div className="space-y-3">
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-muted-foreground">Progress</span>
                      <span className="font-medium">
                        {project.task_count > 0
                          ? Math.round((project.completed_tasks / project.task_count) * 100)
                          : 0}%
                      </span>
                    </div>
                    <Progress
                      value={
                        project.task_count > 0
                          ? (project.completed_tasks / project.task_count) * 100
                          : 0
                      }
                      className="h-2"
                    />
                    <div className="flex items-center gap-4 text-sm text-muted-foreground">
                      <span className="flex items-center gap-1">
                        <FolderKanban className="w-3.5 h-3.5" />
                        {project.task_count} tasks
                      </span>
                      <span className="flex items-center gap-1">
                        <Users className="w-3.5 h-3.5" />
                        {project.team_members?.length || 1}
                      </span>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      ) : (
        <Card>
          <CardContent className="p-0">
            <div className="divide-y divide-border">
              {filteredProjects.map((project) => (
                <div
                  key={project.project_id}
                  className="flex items-center gap-4 p-4 hover:bg-accent cursor-pointer transition-colors"
                  onClick={() => navigate(`/projects/${project.project_id}`)}
                  data-testid={`project-row-${project.project_id}`}
                >
                  <div
                    className="w-10 h-10 rounded-md flex items-center justify-center text-white font-semibold flex-shrink-0"
                    style={{ backgroundColor: project.color }}
                  >
                    {project.name.charAt(0).toUpperCase()}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <h3 className="font-semibold truncate">{project.name}</h3>
                      {getStatusBadge(project.status)}
                    </div>
                    {project.description && (
                      <p className="text-sm text-muted-foreground truncate mt-0.5">
                        {project.description}
                      </p>
                    )}
                  </div>
                  <div className="flex items-center gap-6 text-sm text-muted-foreground">
                    <span>{project.task_count} tasks</span>
                    <div className="w-24">
                      <Progress
                        value={
                          project.task_count > 0
                            ? (project.completed_tasks / project.task_count) * 100
                            : 0
                        }
                        className="h-2"
                      />
                    </div>
                    {project.end_date && (
                      <span className="flex items-center gap-1">
                        <Calendar className="w-3.5 h-3.5" />
                        {format(new Date(project.end_date), "MMM d")}
                      </span>
                    )}
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild onClick={(e) => e.stopPropagation()}>
                        <Button variant="ghost" size="icon" className="h-8 w-8" data-testid={`project-row-menu-${project.project_id}`}>
                          <MoreHorizontal className="w-4 h-4" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end" onClick={(e) => e.stopPropagation()}>
                        {canDo(Permission.PROJECT_EDIT) && (
                          <DropdownMenuItem onClick={(e) => handleOpenEditDialog(project, e)} data-testid={`edit-project-row-${project.project_id}`}>
                            <Pencil className="w-4 h-4 mr-2" />
                            Edit
                          </DropdownMenuItem>
                        )}
                        {canDo(Permission.PROJECT_DELETE) && (
                          <>
                            <DropdownMenuSeparator />
                            <DropdownMenuItem 
                              className="text-destructive focus:text-destructive"
                              onClick={(e) => {
                                e.stopPropagation();
                                setProjectToDelete(project);
                                setDeleteDialogOpen(true);
                              }}
                              data-testid={`delete-project-row-${project.project_id}`}
                            >
                              <Trash2 className="w-4 h-4 mr-2" />
                              Delete
                            </DropdownMenuItem>
                          </>
                        )}
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Delete Confirmation Dialog */}
      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Project</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete "{projectToDelete?.name}"? This action cannot be undone and will remove all associated tasks and data.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel onClick={() => setProjectToDelete(null)} data-testid="cancel-delete-btn">
              Cancel
            </AlertDialogCancel>
            <AlertDialogAction 
              onClick={handleDeleteProject}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
              data-testid="confirm-delete-btn"
            >
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
