import { useState, useEffect } from "react";
import { hasPermission, Permission } from "../api";
import { useAppData } from "../context/AppDataContext";
import { exportTasksReport, exportTimeReport } from "../api/reports";
import { Button } from "../components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../components/ui/card";
import { Label } from "../components/ui/label";
import { Input } from "../components/ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../components/ui/tabs";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../components/ui/select";
import { LoadingSpinner } from "../components/ui/loading-spinner";
import { WorkloadChart } from "../components/WorkloadChart";
import { GanttChart } from "../components/GanttChart";
import { toast } from "sonner";
import { FileJson, FileSpreadsheet, BarChart3, Clock, CalendarDays, Users } from "lucide-react";
import { format, subDays } from "date-fns";

export default function ReportsPage() {
  const {
    organizations,
    projects: globalProjects,
    permissions: globalPermissions,
    currentOrgId,
    loadProjects,
  } = useAppData();
  
  const [loading, setLoading] = useState(true);
  const [exporting, setExporting] = useState(false);
  const [selectedOrg, setSelectedOrg] = useState(null);
  const [selectedProject, setSelectedProject] = useState("all");
  const [taskStatus, setTaskStatus] = useState("all");
  const [startDate, setStartDate] = useState(format(subDays(new Date(), 30), "yyyy-MM-dd"));
  const [endDate, setEndDate] = useState(format(new Date(), "yyyy-MM-dd"));

  // Use global data
  const projects = globalProjects;
  const permissions = globalPermissions;

  // Permission check helper
  const canDo = (permission) => hasPermission(permissions, permission);

  useEffect(() => {
    let isMounted = true;
    
    const loadData = async () => {
      try {
        // Load projects from global context
        await loadProjects();
        
        if (!isMounted) return;
        
        // Set initial org if available
        if (currentOrgId) {
          setSelectedOrg(currentOrgId);
        }
      } catch (error) {
        if (!isMounted) return;
        console.error("Failed to load data:", error);
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
  }, [currentOrgId, loadProjects]);

  // Remove the duplicate useEffect for org data loading since we use global context now

  const downloadBlob = (blob, filename) => {
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const handleExportTasks = async (format) => {
    if (!selectedOrg) {
      toast.error("Please select an organization");
      return;
    }

    setExporting(true);
    try {
      const projectId = selectedProject !== "all" ? selectedProject : null;
      const status = taskStatus !== "all" ? taskStatus : null;
      
      if (format === "csv") {
        const blob = await exportTasksReport(selectedOrg, "csv", projectId, status);
        downloadBlob(blob, `tasks_report_${format(new Date(), "yyyy-MM-dd")}.csv`);
        toast.success("Tasks report exported as CSV");
      } else {
        const data = await exportTasksReport(selectedOrg, "json", projectId, status);
        const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
        downloadBlob(blob, `tasks_report_${format(new Date(), "yyyy-MM-dd")}.json`);
        toast.success("Tasks report exported as JSON");
      }
    } catch (error) {
      toast.error(error.message || "Failed to export tasks report");
    } finally {
      setExporting(false);
    }
  };

  const handleExportTime = async (format) => {
    if (!selectedOrg) {
      toast.error("Please select an organization");
      return;
    }

    setExporting(true);
    try {
      const projectId = selectedProject !== "all" ? selectedProject : null;
      
      if (format === "csv") {
        const blob = await exportTimeReport(selectedOrg, startDate, endDate, "csv", projectId);
        downloadBlob(blob, `time_report_${startDate}_${endDate}.csv`);
        toast.success("Time report exported as CSV");
      } else {
        const data = await exportTimeReport(selectedOrg, startDate, endDate, "json", projectId);
        const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
        downloadBlob(blob, `time_report_${startDate}_${endDate}.json`);
        toast.success("Time report exported as JSON");
      }
    } catch (error) {
      toast.error(error.message || "Failed to export time report");
    } finally {
      setExporting(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-[60vh]">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-fade-in" data-testid="reports-page">
      <div>
        <h1 className="font-heading text-2xl sm:text-3xl font-bold tracking-tight">Reports & Analytics</h1>
        <p className="text-muted-foreground mt-1">Visualize workload, timelines, and export data</p>
      </div>

      <Tabs defaultValue="workload">
        <TabsList>
          <TabsTrigger value="workload" data-testid="workload-tab">
            <Users className="w-4 h-4 mr-2" />
            Workload
          </TabsTrigger>
          <TabsTrigger value="timeline" data-testid="timeline-tab">
            <CalendarDays className="w-4 h-4 mr-2" />
            Timeline
          </TabsTrigger>
          <TabsTrigger value="export" data-testid="export-tab">
            <FileSpreadsheet className="w-4 h-4 mr-2" />
            Export
          </TabsTrigger>
        </TabsList>

        {/* Workload Tab */}
        <TabsContent value="workload" className="mt-6 space-y-6">
          {/* Org Selector */}
          <Card>
            <CardContent className="pt-6">
              <div className="space-y-2 max-w-xs">
                <Label>Organization</Label>
                <Select value={selectedOrg || ""} onValueChange={setSelectedOrg}>
                  <SelectTrigger data-testid="workload-org-select">
                    <SelectValue placeholder="Select organization" />
                  </SelectTrigger>
                  <SelectContent>
                    {organizations.map((org) => (
                      <SelectItem key={org.org_id} value={org.org_id}>
                        {org.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </CardContent>
          </Card>

          {selectedOrg && <WorkloadChart orgId={selectedOrg} />}
        </TabsContent>

        {/* Timeline Tab */}
        <TabsContent value="timeline" className="mt-6 space-y-6">
          <Card>
            <CardContent className="pt-6">
              <div className="space-y-2 max-w-xs">
                <Label>Project</Label>
                <Select 
                  value={selectedProject !== "all" ? selectedProject : ""} 
                  onValueChange={setSelectedProject}
                >
                  <SelectTrigger data-testid="timeline-project-select">
                    <SelectValue placeholder="Select a project" />
                  </SelectTrigger>
                  <SelectContent>
                    {projects.map((proj) => (
                      <SelectItem key={proj.project_id} value={proj.project_id}>
                        {proj.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </CardContent>
          </Card>

          {selectedProject && selectedProject !== "all" && (
            <GanttChart projectId={selectedProject} />
          )}
          
          {(!selectedProject || selectedProject === "all") && (
            <Card>
              <CardContent className="flex items-center justify-center h-[300px] text-muted-foreground">
                Select a project to view its timeline
              </CardContent>
            </Card>
          )}
        </TabsContent>

        {/* Export Tab */}
        <TabsContent value="export" className="mt-6 space-y-6 max-w-4xl">

      {/* Filters */}
      <Card>
        <CardHeader>
          <CardTitle>Report Filters</CardTitle>
          <CardDescription>Select filters for your reports</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid sm:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>Organization</Label>
              <Select value={selectedOrg || ""} onValueChange={setSelectedOrg}>
                <SelectTrigger data-testid="org-select">
                  <SelectValue placeholder="Select organization" />
                </SelectTrigger>
                <SelectContent>
                  {organizations.map((org) => (
                    <SelectItem key={org.org_id} value={org.org_id}>
                      {org.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label>Project</Label>
              <Select value={selectedProject} onValueChange={setSelectedProject}>
                <SelectTrigger data-testid="project-select">
                  <SelectValue placeholder="All projects" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Projects</SelectItem>
                  {projects.map((proj) => (
                    <SelectItem key={proj.project_id} value={proj.project_id}>
                      {proj.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Tasks Report */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <BarChart3 className="w-5 h-5" />
            Tasks Report
          </CardTitle>
          <CardDescription>Export all tasks with status, priority, and assignees</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label>Task Status</Label>
            <Select value={taskStatus} onValueChange={setTaskStatus}>
              <SelectTrigger className="w-[200px]" data-testid="status-select">
                <SelectValue placeholder="All statuses" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Statuses</SelectItem>
                <SelectItem value="todo">To Do</SelectItem>
                <SelectItem value="in_progress">In Progress</SelectItem>
                <SelectItem value="review">In Review</SelectItem>
                <SelectItem value="done">Done</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="flex gap-2">
            {canDo(Permission.REPORT_EXPORT) ? (
              <>
                <Button
                  onClick={() => handleExportTasks("json")}
                  disabled={exporting}
                  variant="outline"
                  data-testid="export-tasks-json"
                >
                  <FileJson className="w-4 h-4 mr-2" />
                  Export JSON
                </Button>
                <Button
                  onClick={() => handleExportTasks("csv")}
                  disabled={exporting}
                  data-testid="export-tasks-csv"
                >
                  <FileSpreadsheet className="w-4 h-4 mr-2" />
                  Export CSV
                </Button>
              </>
            ) : (
              <p className="text-sm text-muted-foreground">You don't have permission to export reports</p>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Time Report */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Clock className="w-5 h-5" />
            Time Tracking Report
          </CardTitle>
          <CardDescription>Export time entries for the selected date range</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid sm:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>Start Date</Label>
              <Input
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                data-testid="start-date"
              />
            </div>
            <div className="space-y-2">
              <Label>End Date</Label>
              <Input
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                data-testid="end-date"
              />
            </div>
          </div>

          <div className="flex gap-2">
            {canDo(Permission.REPORT_EXPORT) ? (
              <>
                <Button
                  onClick={() => handleExportTime("json")}
                  disabled={exporting}
                  variant="outline"
                  data-testid="export-time-json"
                >
                  <FileJson className="w-4 h-4 mr-2" />
                  Export JSON
                </Button>
                <Button
                  onClick={() => handleExportTime("csv")}
                  disabled={exporting}
                  data-testid="export-time-csv"
                >
                  <FileSpreadsheet className="w-4 h-4 mr-2" />
                  Export CSV
                </Button>
              </>
            ) : (
              <p className="text-sm text-muted-foreground">You don't have permission to export reports</p>
            )}
          </div>
        </CardContent>
      </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
