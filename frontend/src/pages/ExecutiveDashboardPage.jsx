import { useState, useEffect } from "react";
import { useAuth } from "../context/AuthContext";
import {
  getOrganizations,
  getMyPermissions,
  hasPermission,
  Permission,
} from "../api";
import {
  getExecutiveDashboard,
  getProductivityTrends,
  getResourceUtilization,
  exportProjects,
  exportTasks,
  exportTimeEntries,
} from "../api/reports";
import { Button } from "../components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../components/ui/card";
import { Badge } from "../components/ui/badge";
import { Progress } from "../components/ui/progress";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../components/ui/select";
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "../components/ui/tabs";
import { LoadingSpinner } from "../components/ui/loading-spinner";
import { toast } from "sonner";
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  AreaChart,
  Area,
} from "recharts";
import {
  LayoutDashboard,
  TrendingUp,
  Users,
  FileText,
  CheckCircle,
  Clock,
  AlertTriangle,
  Download,
  RefreshCw,
  BarChart3,
  Target,
  Activity,
} from "lucide-react";

const COLORS = ["#3b82f6", "#22c55e", "#f59e0b", "#ef4444", "#8b5cf6", "#06b6d4"];

const STATUS_COLORS = {
  planned: "#94a3b8",
  active: "#3b82f6",
  completed: "#22c55e",
  on_hold: "#f59e0b",
  cancelled: "#ef4444",
  todo: "#94a3b8",
  in_progress: "#3b82f6",
  done: "#22c55e",
  blocked: "#ef4444",
};

const PRIORITY_COLORS = {
  low: "#22c55e",
  medium: "#f59e0b",
  high: "#ef4444",
  urgent: "#dc2626",
};

export default function ExecutiveDashboardPage() {
  const { user } = useAuth();
  const [loading, setLoading] = useState(true);
  const [organizations, setOrganizations] = useState([]);
  const [selectedOrg, setSelectedOrg] = useState(null);
  
  // Data states
  const [dashboardData, setDashboardData] = useState(null);
  const [trends, setTrends] = useState([]);
  const [utilization, setUtilization] = useState([]);
  const [trendDays, setTrendDays] = useState(30);
  const [permissions, setPermissions] = useState([]);
  
  // Permission check helper
  const canDo = (permission) => hasPermission(permissions, permission);
  
  // Export states
  const [exporting, setExporting] = useState(null);

  useEffect(() => {
    loadInitialData();
  }, []);

  useEffect(() => {
    if (selectedOrg) {
      loadAllData();
      loadPermissions();
    }
  }, [selectedOrg]);

  useEffect(() => {
    if (selectedOrg) {
      loadTrends();
    }
  }, [trendDays, selectedOrg]);

  const loadInitialData = async () => {
    try {
      const orgsData = await getOrganizations();
      setOrganizations(orgsData);
      if (orgsData.length > 0) {
        setSelectedOrg(orgsData[0]);
      }
    } catch (error) {
      toast.error("Failed to load organizations");
    } finally {
      setLoading(false);
    }
  };

  const loadPermissions = async () => {
    if (!selectedOrg) return;
    try {
      const data = await getMyPermissions(selectedOrg.org_id);
      setPermissions(data.permissions || []);
    } catch (e) {
      setPermissions([]);
    }
  };

  const loadAllData = async () => {
    setLoading(true);
    try {
      const [dashboard, util] = await Promise.all([
        getExecutiveDashboard(selectedOrg.org_id),
        getResourceUtilization(selectedOrg.org_id).catch(() => ({ utilization: [] })),
      ]);
      setDashboardData(dashboard);
      setUtilization(util.utilization || []);
      await loadTrends();
    } catch (error) {
      if (error.message.includes("not available")) {
        toast.error("Advanced reports not available on your plan");
      } else {
        toast.error("Failed to load dashboard data");
      }
    } finally {
      setLoading(false);
    }
  };

  const loadTrends = async () => {
    if (!selectedOrg) return;
    try {
      const data = await getProductivityTrends(selectedOrg.org_id, trendDays);
      setTrends(data.trends || []);
    } catch (error) {
      console.error("Failed to load trends:", error);
    }
  };

  const handleExport = async (type, format = "csv") => {
    setExporting(type);
    try {
      let blob;
      switch (type) {
        case "projects":
          blob = await exportProjects(selectedOrg.org_id, format);
          break;
        case "tasks":
          blob = await exportTasks(selectedOrg.org_id, format);
          break;
        case "time":
          blob = await exportTimeEntries(selectedOrg.org_id, format);
          break;
        default:
          return;
      }

      if (format === "csv") {
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `${type}_${selectedOrg.org_id}_${new Date().toISOString().split("T")[0]}.csv`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
      }

      toast.success(`Exported ${type} successfully`);
    } catch (error) {
      toast.error(`Failed to export ${type}`);
    } finally {
      setExporting(null);
    }
  };

  // Prepare chart data
  const projectStatusData = dashboardData?.projects?.by_status
    ? Object.entries(dashboardData.projects.by_status).map(([name, value]) => ({
        name: name.replace(/_/g, " "),
        value,
        color: STATUS_COLORS[name] || COLORS[0],
      }))
    : [];

  const taskStatusData = dashboardData?.tasks?.by_status
    ? Object.entries(dashboardData.tasks.by_status).map(([name, value]) => ({
        name: name.replace(/_/g, " "),
        value,
        color: STATUS_COLORS[name] || COLORS[0],
      }))
    : [];

  const taskPriorityData = dashboardData?.tasks?.by_priority
    ? Object.entries(dashboardData.tasks.by_priority).map(([name, value]) => ({
        name,
        value,
        color: PRIORITY_COLORS[name] || COLORS[0],
      }))
    : [];

  if (loading && !dashboardData) {
    return (
      <div className="flex items-center justify-center h-[60vh]">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="executive-dashboard-page">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <LayoutDashboard className="h-6 w-6 text-indigo-500" />
            Executive Dashboard
          </h1>
          <p className="text-muted-foreground">
            High-level overview of your organization's performance
          </p>
        </div>
        <div className="flex items-center gap-2">
          {organizations.length > 1 && (
            <Select value={selectedOrg?.org_id} onValueChange={(val) => setSelectedOrg(organizations.find(o => o.org_id === val))}>
              <SelectTrigger className="w-48">
                <SelectValue placeholder="Select organization" />
              </SelectTrigger>
              <SelectContent>
                {organizations.map((org) => (
                  <SelectItem key={org.org_id} value={org.org_id}>{org.name}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          )}
          <Button variant="outline" onClick={loadAllData} disabled={loading}>
            <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
          </Button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Total Projects</p>
                <p className="text-3xl font-bold">{dashboardData?.projects?.total || 0}</p>
                <p className="text-xs text-muted-foreground mt-1">
                  {dashboardData?.projects?.by_status?.active || 0} active
                </p>
              </div>
              <FileText className="h-10 w-10 text-blue-500 opacity-50" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Total Tasks</p>
                <p className="text-3xl font-bold">{dashboardData?.tasks?.total || 0}</p>
                <p className="text-xs text-muted-foreground mt-1">
                  {dashboardData?.tasks?.in_progress || 0} in progress
                </p>
              </div>
              <CheckCircle className="h-10 w-10 text-green-500 opacity-50" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Completion Rate</p>
                <p className="text-3xl font-bold">{dashboardData?.tasks?.completion_rate || 0}%</p>
                <Progress value={dashboardData?.tasks?.completion_rate || 0} className="mt-2 h-2" />
              </div>
              <Target className="h-10 w-10 text-purple-500 opacity-50" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Overdue Tasks</p>
                <p className="text-3xl font-bold text-red-500">{dashboardData?.tasks?.overdue || 0}</p>
                <p className="text-xs text-muted-foreground mt-1">
                  Needs attention
                </p>
              </div>
              <AlertTriangle className="h-10 w-10 text-red-500 opacity-50" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Tabs for different views */}
      <Tabs defaultValue="overview" className="space-y-4">
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="trends">Productivity Trends</TabsTrigger>
          <TabsTrigger value="workload">Team Workload</TabsTrigger>
          <TabsTrigger value="export">Export Data</TabsTrigger>
        </TabsList>

        {/* Overview Tab */}
        <TabsContent value="overview" className="space-y-4">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            {/* Projects by Status */}
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Projects by Status</CardTitle>
              </CardHeader>
              <CardContent>
                {projectStatusData.length > 0 ? (
                  <ResponsiveContainer width="100%" height={200}>
                    <PieChart>
                      <Pie
                        data={projectStatusData}
                        cx="50%"
                        cy="50%"
                        innerRadius={40}
                        outerRadius={70}
                        paddingAngle={2}
                        dataKey="value"
                        label={({ name, value }) => `${name}: ${value}`}
                      >
                        {projectStatusData.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={entry.color} />
                        ))}
                      </Pie>
                      <Tooltip />
                    </PieChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="h-[200px] flex items-center justify-center text-muted-foreground">
                    No project data
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Tasks by Status */}
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Tasks by Status</CardTitle>
              </CardHeader>
              <CardContent>
                {taskStatusData.length > 0 ? (
                  <ResponsiveContainer width="100%" height={200}>
                    <BarChart data={taskStatusData}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="name" fontSize={10} />
                      <YAxis />
                      <Tooltip />
                      <Bar dataKey="value" name="Tasks">
                        {taskStatusData.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={entry.color} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="h-[200px] flex items-center justify-center text-muted-foreground">
                    No task data
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Tasks by Priority */}
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Tasks by Priority</CardTitle>
              </CardHeader>
              <CardContent>
                {taskPriorityData.length > 0 ? (
                  <ResponsiveContainer width="100%" height={200}>
                    <PieChart>
                      <Pie
                        data={taskPriorityData}
                        cx="50%"
                        cy="50%"
                        outerRadius={70}
                        paddingAngle={2}
                        dataKey="value"
                        label={({ name, value }) => `${name}: ${value}`}
                      >
                        {taskPriorityData.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={entry.color} />
                        ))}
                      </Pie>
                      <Tooltip />
                    </PieChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="h-[200px] flex items-center justify-center text-muted-foreground">
                    No priority data
                  </div>
                )}
              </CardContent>
            </Card>
          </div>

          {/* Top Workload */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Team Workload (Top 10)</CardTitle>
              <CardDescription>Tasks assigned to each team member</CardDescription>
            </CardHeader>
            <CardContent>
              {dashboardData?.workload?.length > 0 ? (
                <div className="space-y-3">
                  {dashboardData.workload.map((member, index) => (
                    <div key={member.user_id || index} className="flex items-center gap-4">
                      <div className="w-32 truncate text-sm">{member.name}</div>
                      <div className="flex-1">
                        <div className="flex gap-1 h-5">
                          {member.completed > 0 && (
                            <div
                              className="bg-green-500 rounded"
                              style={{ width: `${(member.completed / member.total_tasks) * 100}%` }}
                              title={`Completed: ${member.completed}`}
                            />
                          )}
                          {member.in_progress > 0 && (
                            <div
                              className="bg-blue-500 rounded"
                              style={{ width: `${(member.in_progress / member.total_tasks) * 100}%` }}
                              title={`In Progress: ${member.in_progress}`}
                            />
                          )}
                          {member.overdue > 0 && (
                            <div
                              className="bg-red-500 rounded"
                              style={{ width: `${(member.overdue / member.total_tasks) * 100}%` }}
                              title={`Overdue: ${member.overdue}`}
                            />
                          )}
                        </div>
                      </div>
                      <div className="text-sm text-muted-foreground w-20 text-right">
                        {member.total_tasks} tasks
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-center text-muted-foreground py-8">No workload data</p>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Trends Tab */}
        <TabsContent value="trends" className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-medium">Productivity Over Time</h3>
            <Select value={String(trendDays)} onValueChange={(val) => setTrendDays(parseInt(val))}>
              <SelectTrigger className="w-32">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="7">Last 7 days</SelectItem>
                <SelectItem value="14">Last 14 days</SelectItem>
                <SelectItem value="30">Last 30 days</SelectItem>
                <SelectItem value="60">Last 60 days</SelectItem>
                <SelectItem value="90">Last 90 days</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <Card>
            <CardContent className="pt-6">
              {trends.length > 0 ? (
                <ResponsiveContainer width="100%" height={350}>
                  <AreaChart data={trends}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="date" fontSize={10} tickFormatter={(val) => val.slice(5)} />
                    <YAxis />
                    <Tooltip />
                    <Legend />
                    <Area type="monotone" dataKey="created" name="Tasks Created" stroke="#3b82f6" fill="#3b82f680" />
                    <Area type="monotone" dataKey="completed" name="Tasks Completed" stroke="#22c55e" fill="#22c55e80" />
                  </AreaChart>
                </ResponsiveContainer>
              ) : (
                <div className="h-[350px] flex items-center justify-center text-muted-foreground">
                  No trend data available
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Workload Tab */}
        <TabsContent value="workload" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Resource Utilization</CardTitle>
              <CardDescription>Team member workload and time tracking</CardDescription>
            </CardHeader>
            <CardContent>
              {utilization.length > 0 ? (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b">
                        <th className="text-left py-2">Team Member</th>
                        <th className="text-center py-2">Active Tasks</th>
                        <th className="text-center py-2">Estimated Hours</th>
                        <th className="text-center py-2">Actual Hours</th>
                        <th className="text-center py-2">Utilization</th>
                      </tr>
                    </thead>
                    <tbody>
                      {utilization.map((member, index) => (
                        <tr key={member.user_id || index} className="border-b last:border-0">
                          <td className="py-3">{member.name}</td>
                          <td className="text-center py-3">{member.active_tasks}</td>
                          <td className="text-center py-3">{member.estimated_hours}h</td>
                          <td className="text-center py-3">{member.actual_hours}h</td>
                          <td className="py-3">
                            <div className="flex items-center justify-center gap-2">
                              <Progress value={Math.min(member.utilization_rate, 100)} className="w-20 h-2" />
                              <span className={`text-xs ${member.utilization_rate > 100 ? 'text-red-500' : ''}`}>
                                {member.utilization_rate}%
                              </span>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <p className="text-center text-muted-foreground py-8">No utilization data available</p>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Export Tab */}
        <TabsContent value="export" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Export Data</CardTitle>
              <CardDescription>Download your organization's data in CSV or JSON format</CardDescription>
            </CardHeader>
            <CardContent>
              {canDo(Permission.REPORT_EXPORT) ? (
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <Card className="border-dashed">
                    <CardContent className="pt-6 text-center">
                      <FileText className="h-10 w-10 mx-auto mb-3 text-blue-500" />
                      <h4 className="font-medium mb-2">Projects</h4>
                      <p className="text-xs text-muted-foreground mb-4">
                        Export all projects with status and dates
                      </p>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleExport("projects")}
                        disabled={exporting === "projects"}
                        data-testid="export-projects-btn"
                      >
                        {exporting === "projects" ? <LoadingSpinner size="sm" className="mr-2" /> : <Download className="h-4 w-4 mr-2" />}
                        Export CSV
                      </Button>
                    </CardContent>
                  </Card>

                  <Card className="border-dashed">
                    <CardContent className="pt-6 text-center">
                      <CheckCircle className="h-10 w-10 mx-auto mb-3 text-green-500" />
                      <h4 className="font-medium mb-2">Tasks</h4>
                      <p className="text-xs text-muted-foreground mb-4">
                        Export all tasks with assignees and status
                      </p>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleExport("tasks")}
                        disabled={exporting === "tasks"}
                        data-testid="export-tasks-btn"
                      >
                        {exporting === "tasks" ? <LoadingSpinner size="sm" className="mr-2" /> : <Download className="h-4 w-4 mr-2" />}
                        Export CSV
                      </Button>
                    </CardContent>
                  </Card>

                  <Card className="border-dashed">
                    <CardContent className="pt-6 text-center">
                      <Clock className="h-10 w-10 mx-auto mb-3 text-purple-500" />
                      <h4 className="font-medium mb-2">Time Entries</h4>
                      <p className="text-xs text-muted-foreground mb-4">
                        Export time tracking data
                      </p>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleExport("time")}
                        disabled={exporting === "time"}
                        data-testid="export-time-btn"
                      >
                        {exporting === "time" ? <LoadingSpinner size="sm" className="mr-2" /> : <Download className="h-4 w-4 mr-2" />}
                        Export CSV
                      </Button>
                    </CardContent>
                  </Card>
                </div>
              ) : (
                <div className="text-center py-8 text-muted-foreground">
                  <Download className="h-12 w-12 mx-auto mb-4 opacity-50" />
                  <p>You don't have permission to export data.</p>
                  <p className="text-sm">Contact your organization admin for access.</p>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
