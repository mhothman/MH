import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { getOrganizations, getMyPermissions, hasPermission, Permission } from "../api";
import { getDashboard } from "../api/dashboard";
import { getProjects } from "../api/projects";
import { getPendingDocumentApprovals, getOrgDocumentApprovals, getStatusColor, getStatusLabel } from "../api/documents";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Badge } from "../components/ui/badge";
import { Progress } from "../components/ui/progress";
import { LoadingSpinner } from "../components/ui/loading-spinner";
import {
  FolderKanban,
  CheckCircle2,
  Clock,
  AlertTriangle,
  TrendingUp,
  ArrowRight,
  Plus,
  FileText,
  Shield,
} from "lucide-react";
import { formatDistanceToNow } from "date-fns";

export default function DashboardPage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [dashboard, setDashboard] = useState(null);
  const [projects, setProjects] = useState([]);
  const [permissions, setPermissions] = useState([]);
  const [pendingApprovals, setPendingApprovals] = useState([]);
  const [currentOrgId, setCurrentOrgId] = useState(null);

  // Permission check helper
  const canDo = (permission) => hasPermission(permissions, permission);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [dashboardData, projectsData, orgsData] = await Promise.all([
        getDashboard(),
        getProjects(),
        getOrganizations(),
      ]);
      setDashboard(dashboardData);
      setProjects(projectsData.slice(0, 4));
      
      // Load permissions and pending approvals if org exists
      if (orgsData.length > 0) {
        const orgId = orgsData[0].org_id;
        setCurrentOrgId(orgId);
        
        try {
          const [permData, approvalsData] = await Promise.all([
            getMyPermissions(orgId),
            // Get all pending approvals for admins (they can force approve)
            getOrgDocumentApprovals(orgId, 'pending', 5).catch(() => []),
          ]);
          setPermissions(permData.permissions || []);
          setPendingApprovals(approvalsData.slice(0, 5) || []);
        } catch (e) {
          setPermissions([]);
          setPendingApprovals([]);
        }
      }
    } catch (error) {
      console.error("Failed to load dashboard:", error);
    } finally {
      setLoading(false);
    }
  };

  const getPriorityColor = (priority) => {
    const colors = {
      urgent: "bg-red-500",
      high: "bg-orange-500",
      medium: "bg-yellow-500",
      low: "bg-green-500",
    };
    return colors[priority] || colors.medium;
  };

  const getStatusBadge = (status) => {
    const variants = {
      todo: "secondary",
      in_progress: "default",
      review: "outline",
      done: "default",
    };
    const labels = {
      todo: "To Do",
      in_progress: "In Progress",
      review: "In Review",
      done: "Done",
    };
    return (
      <Badge variant={variants[status] || "secondary"}>
        {labels[status] || status}
      </Badge>
    );
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-[60vh]">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  const stats = [
    {
      title: "Total Projects",
      value: dashboard?.projects?.total || 0,
      subtitle: `${dashboard?.projects?.active || 0} active`,
      icon: FolderKanban,
      color: "text-blue-500",
    },
    {
      title: "Tasks Completed",
      value: dashboard?.tasks?.completed || 0,
      subtitle: `${dashboard?.tasks?.completion_rate || 0}% completion rate`,
      icon: CheckCircle2,
      color: "text-green-500",
    },
    {
      title: "In Progress",
      value: dashboard?.tasks?.by_status?.in_progress || 0,
      subtitle: `${dashboard?.tasks?.assigned_to_me || 0} assigned to you`,
      icon: Clock,
      color: "text-yellow-500",
    },
    {
      title: "Overdue",
      value: dashboard?.tasks?.overdue || 0,
      subtitle: "Tasks past due date",
      icon: AlertTriangle,
      color: "text-red-500",
    },
  ];

  return (
    <div className="space-y-8 animate-fade-in" data-testid="dashboard-page">
      {/* Welcome Section */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-heading text-2xl sm:text-3xl font-bold tracking-tight">
            Welcome back, {user?.name?.split(" ")[0] || "User"}
          </h1>
          <p className="text-muted-foreground mt-1">
            Here&apos;s what&apos;s happening with your projects
          </p>
        </div>
        {canDo(Permission.PROJECT_CREATE) && (
          <Button onClick={() => navigate("/projects")} data-testid="view-projects-btn">
            <Plus className="w-4 h-4 mr-2" />
            New Project
          </Button>
        )}
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {stats.map((stat, index) => (
          <Card key={index} className="stat-card" data-testid={`stat-${stat.title.toLowerCase().replace(/\s/g, '-')}`}>
            <CardContent className="pt-6">
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">{stat.title}</p>
                  <p className="text-3xl font-bold tracking-tight mt-1">{stat.value}</p>
                  <p className="text-xs text-muted-foreground mt-1">{stat.subtitle}</p>
                </div>
                <div className={`p-2 rounded-lg bg-muted ${stat.color}`}>
                  <stat.icon className="w-5 h-5" />
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="grid lg:grid-cols-2 gap-6">
        {/* Recent Projects */}
        <Card data-testid="recent-projects-card">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="font-heading text-lg">Recent Projects</CardTitle>
            <Button variant="ghost" size="sm" onClick={() => navigate("/projects")}>
              View All
              <ArrowRight className="w-4 h-4 ml-1" />
            </Button>
          </CardHeader>
          <CardContent>
            {projects.length === 0 ? (
              <div className="empty-state py-8">
                <FolderKanban className="empty-state-icon" />
                <p className="text-muted-foreground">No projects yet</p>
                <Button variant="outline" className="mt-4" onClick={() => navigate("/projects")}>
                  Create your first project
                </Button>
              </div>
            ) : (
              <div className="space-y-4">
                {projects.map((project) => (
                  <div
                    key={project.project_id}
                    className="flex items-center gap-4 p-3 rounded-lg hover:bg-accent cursor-pointer transition-colors"
                    onClick={() => navigate(`/projects/${project.project_id}`)}
                    data-testid={`project-${project.project_id}`}
                  >
                    <div
                      className="w-10 h-10 rounded-md flex items-center justify-center text-white font-semibold"
                      style={{ backgroundColor: project.color }}
                    >
                      {project.name.charAt(0).toUpperCase()}
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="font-medium truncate">{project.name}</p>
                      <p className="text-sm text-muted-foreground">
                        {project.task_count} tasks · {project.completed_tasks} completed
                      </p>
                    </div>
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
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Recent Activity */}
        <Card data-testid="recent-activity-card">
          <CardHeader className="pb-2">
            <CardTitle className="font-heading text-lg">Recent Activity</CardTitle>
          </CardHeader>
          <CardContent>
            {dashboard?.recent_tasks?.length === 0 ? (
              <div className="empty-state py-8">
                <TrendingUp className="empty-state-icon" />
                <p className="text-muted-foreground">No recent activity</p>
              </div>
            ) : (
              <div className="space-y-3">
                {dashboard?.recent_tasks?.map((task) => (
                  <div
                    key={task.task_id}
                    className="flex items-start gap-3 p-2 rounded-lg hover:bg-accent cursor-pointer transition-colors"
                    data-testid={`activity-${task.task_id}`}
                  >
                    <div className={`w-2 h-2 rounded-full mt-2 ${getPriorityColor(task.priority)}`} />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium truncate">{task.title}</p>
                      <div className="flex items-center gap-2 mt-1">
                        {getStatusBadge(task.status)}
                        <span className="text-xs text-muted-foreground">
                          {formatDistanceToNow(new Date(task.updated_at), { addSuffix: true })}
                        </span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Pending Approvals Widget */}
      {pendingApprovals.length > 0 && (
        <Card data-testid="pending-approvals-card" className="border-amber-200 bg-amber-50/30 dark:bg-amber-950/20 dark:border-amber-800">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <div className="flex items-center gap-2">
              <Shield className="w-5 h-5 text-amber-600" />
              <CardTitle className="font-heading text-lg text-amber-800 dark:text-amber-200">
                Pending Approvals
              </CardTitle>
              <Badge variant="secondary" className="bg-amber-100 text-amber-800 dark:bg-amber-800 dark:text-amber-100">
                {pendingApprovals.length}
              </Badge>
            </div>
            <Button variant="ghost" size="sm" onClick={() => navigate("/documents")}>
              View All
              <ArrowRight className="w-4 h-4 ml-1" />
            </Button>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {pendingApprovals.map((approval) => (
                <div
                  key={approval.approval_id}
                  className="flex items-center gap-4 p-3 rounded-lg bg-white dark:bg-gray-800 border cursor-pointer hover:shadow-sm transition-shadow"
                  onClick={() => navigate("/documents")}
                  data-testid={`pending-approval-${approval.approval_id}`}
                >
                  <div className="w-10 h-10 rounded-lg bg-amber-100 dark:bg-amber-800 flex items-center justify-center">
                    <FileText className="w-5 h-5 text-amber-600 dark:text-amber-200" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="font-medium truncate">{approval.document_title}</p>
                    <div className="flex items-center gap-2 text-sm text-muted-foreground mt-1">
                      <span>Requested by {approval.requester_name}</span>
                      <span>•</span>
                      <Badge 
                        variant="outline" 
                        style={{ 
                          borderColor: getStatusColor(approval.target_status), 
                          color: getStatusColor(approval.target_status) 
                        }}
                        className="text-xs"
                      >
                        → {getStatusLabel(approval.target_status)}
                      </Badge>
                    </div>
                  </div>
                  <div className="flex items-center gap-1 text-amber-600">
                    <Clock className="w-4 h-4" />
                    <span className="text-xs">
                      {formatDistanceToNow(new Date(approval.created_at), { addSuffix: true })}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
