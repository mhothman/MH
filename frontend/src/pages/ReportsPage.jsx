import { useState, useEffect } from "react";
import { useAppData } from "../context/AppDataContext";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Label } from "../components/ui/label";
import { Input } from "../components/ui/input";
import { Badge } from "../components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../components/ui/tabs";
import { LoadingSpinner } from "../components/ui/loading-spinner";
import { Progress } from "../components/ui/progress";
import { 
  FileDown, 
  FileText, 
  Calendar, 
  Users, 
  DollarSign, 
  TrendingUp, 
  Filter,
  Clock,
  AlertTriangle,
  CheckCircle2,
  BarChart3
} from "lucide-react";
import { toast } from "sonner";
import { format, subDays } from "date-fns";

const REPORT_TYPES = [
  { id: "time-tracking", label: "Time Tracking", icon: Clock, description: "Detailed time logs and summaries" },
  { id: "budget-summary", label: "Budget Summary", icon: DollarSign, description: "Budget status across projects" },
  { id: "project-progress", label: "Project Progress", icon: TrendingUp, description: "Project completion metrics" },
  { id: "task-completion", label: "Task Completion Rates", icon: CheckCircle2, description: "Task completion analysis" },
  { id: "delays-bottlenecks", label: "Delays & Bottlenecks", icon: AlertTriangle, description: "Identify delays and bottlenecks" },
  { id: "team-productivity", label: "Team Productivity", icon: Users, description: "Team performance metrics" },
];

export default function ReportsPage() {
  const { currentOrgId, projects, loadProjects } = useAppData();
  const [selectedReport, setSelectedReport] = useState("time-tracking");
  const [startDate, setStartDate] = useState(format(subDays(new Date(), 30), "yyyy-MM-dd"));
  const [endDate, setEndDate] = useState(format(new Date(), "yyyy-MM-dd"));
  const [groupBy, setGroupBy] = useState("project");
  const [selectedProjects, setSelectedProjects] = useState([]);
  const [loading, setLoading] = useState(false);
  const [reportData, setReportData] = useState(null);
  const [showPreview, setShowPreview] = useState(false);

  useEffect(() => {
    loadProjects();
  }, []);

  const handleExport = async (format) => {
    if (!currentOrgId) {
      toast.error("Please select an organization");
      return;
    }

    if (!reportData) {
      toast.error("Please generate a report first");
      return;
    }

    setLoading(true);
    try {
      const API_URL = process.env.REACT_APP_BACKEND_URL;
      const token = localStorage.getItem('proflow_token');
      
      let url = `${API_URL}/api/custom-reports/${selectedReport}?org_id=${currentOrgId}`;
      
      if (selectedReport === "time-tracking") {
        if (startDate) url += `&start_date=${startDate}`;
        if (endDate) url += `&end_date=${endDate}`;
        url += `&group_by=${groupBy}`;
      }
      
      if (selectedProjects.length > 0) {
        url += `&project_ids=${selectedProjects.join(',')}`;
      }
      
      url += `&export_format=${format}`;
      
      const response = await fetch(url, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      
      if (!response.ok) throw new Error('Export failed');
      
      const blob = await response.blob();
      const downloadUrl = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = downloadUrl;
      a.download = `${selectedReport}_${new Date().toISOString().split('T')[0]}.${format}`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(downloadUrl);
      
      toast.success(`Report exported as ${format.toUpperCase()}`);
    } catch (error) {
      toast.error(error.message || "Failed to export report");
    } finally {
      setLoading(false);
    }
  };

  const handlePreview = async () => {
    if (!currentOrgId) {
      toast.error("Please select an organization");
      return;
    }

    setLoading(true);
    setShowPreview(false);
    try {
      const API_URL = process.env.REACT_APP_BACKEND_URL;
      const token = localStorage.getItem('proflow_token');
      
      let url = `${API_URL}/api/custom-reports/${selectedReport}?org_id=${currentOrgId}`;
      
      if (selectedReport === "time-tracking") {
        if (startDate) url += `&start_date=${startDate}`;
        if (endDate) url += `&end_date=${endDate}`;
        url += `&group_by=${groupBy}`;
      }
      
      if (selectedProjects.length > 0) {
        url += `&project_ids=${selectedProjects.join(',')}`;
      }
      
      const response = await fetch(url, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      
      if (!response.ok) throw new Error('Failed to generate report');
      
      const data = await response.json();
      setReportData(data);
      setShowPreview(true);
      toast.success("Report generated successfully");
    } catch (error) {
      toast.error(error.message || "Failed to generate report");
      setReportData(null);
    } finally {
      setLoading(false);
    }
  };

  const selectedReportConfig = REPORT_TYPES.find(r => r.id === selectedReport);
  const ReportIcon = selectedReportConfig?.icon || FileText;

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center gap-3">
        <BarChart3 className="w-8 h-8 text-blue-600" />
        <div>
          <h1 className="font-heading text-2xl sm:text-3xl font-bold tracking-tight">
            Reports & Analytics
          </h1>
          <p className="text-muted-foreground mt-1">
            Generate comprehensive reports with export capabilities
          </p>
        </div>
      </div>

      <Tabs value={selectedReport} onValueChange={setSelectedReport} className="w-full">
        <TabsList className="grid w-full grid-cols-3 lg:grid-cols-6">
          {REPORT_TYPES.map((report) => {
            const Icon = report.icon;
            return (
              <TabsTrigger key={report.id} value={report.id} className="text-xs sm:text-sm">
                <Icon className="w-4 h-4 mr-1" />
                <span className="hidden sm:inline">{report.label}</span>
                <span className="sm:hidden">{report.label.split(' ')[0]}</span>
              </TabsTrigger>
            );
          })}
        </TabsList>

        {REPORT_TYPES.map((report) => (
          <TabsContent key={report.id} value={report.id} className="space-y-4">
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle className="text-lg flex items-center gap-2">
                      <report.icon className="w-5 h-5 text-primary" />
                      {report.label}
                    </CardTitle>
                    <CardDescription>{report.description}</CardDescription>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="space-y-6">
                {/* Filters Section */}
                <div className="space-y-4 p-4 bg-muted/30 rounded-lg">
                  <h3 className="font-medium flex items-center gap-2">
                    <Filter className="w-4 h-4" />
                    Filters
                  </h3>
                  
                  {/* Date Range (for time-based reports) */}
                  {["time-tracking", "task-completion", "delays-bottlenecks", "team-productivity"].includes(report.id) && (
                    <div className="grid grid-cols-2 gap-4">
                      <div className="space-y-2">
                        <Label>Start Date</Label>
                        <Input
                          type="date"
                          value={startDate}
                          onChange={(e) => setStartDate(e.target.value)}
                        />
                      </div>
                      <div className="space-y-2">
                        <Label>End Date</Label>
                        <Input
                          type="date"
                          value={endDate}
                          onChange={(e) => setEndDate(e.target.value)}
                        />
                      </div>
                    </div>
                  )}
                  
                  {/* Group By (for time tracking) */}
                  {report.id === "time-tracking" && (
                    <div className="space-y-2">
                      <Label>Group By</Label>
                      <Select value={groupBy} onValueChange={setGroupBy}>
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="project">Project</SelectItem>
                          <SelectItem value="user">User</SelectItem>
                          <SelectItem value="date">Date</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                  )}
                  
                  {/* Project Filter */}
                  <div className="space-y-2">
                    <Label>Filter by Projects (Optional)</Label>
                    <div className="flex flex-wrap gap-2 p-3 border rounded-lg min-h-[60px]">
                      {projects.slice(0, 15).map((project) => (
                        <Badge
                          key={project.project_id}
                          variant={selectedProjects.includes(project.project_id) ? "default" : "outline"}
                          className="cursor-pointer"
                          onClick={() => {
                            if (selectedProjects.includes(project.project_id)) {
                              setSelectedProjects(selectedProjects.filter(id => id !== project.project_id));
                            } else {
                              setSelectedProjects([...selectedProjects, project.project_id]);
                            }
                          }}
                        >
                          {project.name}
                        </Badge>
                      ))}
                      {selectedProjects.length > 0 && (
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => setSelectedProjects([])}
                          className="h-6 text-xs"
                        >
                          Clear All
                        </Button>
                      )}
                    </div>
                  </div>
                </div>

                {/* Actions */}
                <div className="flex gap-3">
                  <Button onClick={handlePreview} disabled={loading}>
                    {loading ? <LoadingSpinner size="sm" className="mr-2" /> : null}
                    Generate Report
                  </Button>
                  {showPreview && reportData && (
                    <>
                      <Button onClick={() => handleExport('csv')} disabled={loading} variant="outline">
                        <FileDown className="w-4 h-4 mr-2" />
                        Export CSV
                      </Button>
                      <Button onClick={() => toast.info('PDF export coming soon')} disabled={loading} variant="outline">
                        <FileDown className="w-4 h-4 mr-2" />
                        Export PDF
                      </Button>
                      <Button onClick={() => toast.info('Excel export coming soon')} disabled={loading} variant="outline">
                        <FileDown className="w-4 h-4 mr-2" />
                        Export Excel
                      </Button>
                    </>
                  )}
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        ))}
      </Tabs>

      {/* Report Preview Section */}
      {showPreview && reportData && (
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="text-lg">Report Results</CardTitle>
              <div className="text-sm text-muted-foreground">
                {selectedReport === "time-tracking" && `Total: ${reportData.total_hours || 0}h`}
                {selectedReport === "budget-summary" && `Total Budget: E£${reportData.summary?.total_budget?.toLocaleString() || 0}`}
                {selectedReport === "project-progress" && `Projects: ${reportData.summary?.total_projects || 0}`}
                {selectedReport === "task-completion" && `Completion Rate: ${reportData.summary?.avg_completion_rate?.toFixed(1) || 0}%`}
                {selectedReport === "team-productivity" && `Total Hours: ${reportData.total_hours || 0}h`}
              </div>
            </div>
          </CardHeader>
          <CardContent>
            {/* Time Tracking Report */}
            {selectedReport === "time-tracking" && reportData.grouped_data && (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>{groupBy === "project" ? "Project" : groupBy === "user" ? "User" : "Date"}</TableHead>
                    <TableHead className="text-right">Entries</TableHead>
                    <TableHead className="text-right">Total Hours</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {reportData.grouped_data.map((row, idx) => (
                    <TableRow key={idx}>
                      <TableCell className="font-medium">
                        {row.project_name || row.user_name || row.date || "Unknown"}
                      </TableCell>
                      <TableCell className="text-right">{row.entry_count || 0}</TableCell>
                      <TableCell className="text-right font-mono">{row.total_hours?.toFixed(2) || 0}h</TableCell>
                    </TableRow>
                  ))}
                  <TableRow className="bg-muted/50 font-semibold">
                    <TableCell>Total</TableCell>
                    <TableCell className="text-right">
                      {reportData.grouped_data.reduce((sum, row) => sum + (row.entry_count || 0), 0)}
                    </TableCell>
                    <TableCell className="text-right font-mono">{reportData.total_hours?.toFixed(2) || 0}h</TableCell>
                  </TableRow>
                </TableBody>
              </Table>
            )}

            {/* Budget Summary Report */}
            {selectedReport === "budget-summary" && reportData.budgets && (
              <>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Project</TableHead>
                      <TableHead className="text-right">Total Budget</TableHead>
                      <TableHead className="text-right">Spent</TableHead>
                      <TableHead className="text-right">Remaining</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead className="text-right">Progress</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {reportData.budgets.map((budget, idx) => (
                      <TableRow key={idx}>
                        <TableCell className="font-medium">{budget.project_name || "Unknown"}</TableCell>
                        <TableCell className="text-right">{budget.currency} {budget.total_budget?.toLocaleString() || 0}</TableCell>
                        <TableCell className="text-right">{budget.currency} {budget.spent_amount?.toLocaleString() || 0}</TableCell>
                        <TableCell className="text-right">{budget.currency} {budget.remaining_amount?.toLocaleString() || 0}</TableCell>
                        <TableCell>
                          <Badge variant={
                            budget.status === "exceeded" ? "destructive" :
                            budget.status === "warning" ? "default" :
                            "secondary"
                          }>
                            {budget.status}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-right">
                          <div className="flex items-center gap-2">
                            <Progress value={Math.min(budget.spent_percent || 0, 100)} className="h-2 w-24" />
                            <span className="font-mono text-sm">{budget.spent_percent?.toFixed(1) || 0}%</span>
                          </div>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
                
                <div className="mt-4 p-4 bg-muted rounded-lg grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div>
                    <p className="text-xs text-muted-foreground">Total Budget</p>
                    <p className="text-lg font-bold">E£{reportData.summary?.total_budget?.toLocaleString() || 0}</p>
                  </div>
                  <div>
                    <p className="text-xs text-muted-foreground">Total Spent</p>
                    <p className="text-lg font-bold">E£{reportData.summary?.total_spent?.toLocaleString() || 0}</p>
                  </div>
                  <div>
                    <p className="text-xs text-muted-foreground">At Risk</p>
                    <p className="text-lg font-bold text-yellow-600">
                      {(reportData.summary?.warning_count || 0) + (reportData.summary?.exceeded_count || 0)}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs text-muted-foreground">Total Projects</p>
                    <p className="text-lg font-bold">{reportData.summary?.total_projects || 0}</p>
                  </div>
                </div>
              </>
            )}

            {/* Project Progress Report */}
            {selectedReport === "project-progress" && reportData.projects && (
              <>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Project</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead className="text-right">Total</TableHead>
                      <TableHead className="text-right">Completed</TableHead>
                      <TableHead className="text-right">In Progress</TableHead>
                      <TableHead className="text-right">To Do</TableHead>
                      <TableHead className="text-right">Completion</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {reportData.projects.map((project, idx) => (
                      <TableRow key={idx}>
                        <TableCell className="font-medium">{project.name || "Unknown"}</TableCell>
                        <TableCell><Badge variant="outline">{project.status}</Badge></TableCell>
                        <TableCell className="text-right">{project.total_tasks || 0}</TableCell>
                        <TableCell className="text-right text-green-600 font-medium">{project.completed_tasks || 0}</TableCell>
                        <TableCell className="text-right text-yellow-600 font-medium">{project.in_progress_tasks || 0}</TableCell>
                        <TableCell className="text-right">{project.todo_tasks || 0}</TableCell>
                        <TableCell className="text-right">
                          <div className="flex items-center gap-2">
                            <Progress value={project.completion_rate || 0} className="h-2 w-20" />
                            <span className="font-mono text-sm">{project.completion_rate?.toFixed(1) || 0}%</span>
                          </div>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
                
                <div className="mt-4 p-4 bg-muted rounded-lg grid grid-cols-3 gap-4">
                  <div>
                    <p className="text-xs text-muted-foreground">Average Completion</p>
                    <p className="text-lg font-bold">{reportData.summary?.avg_completion_rate?.toFixed(1) || 0}%</p>
                  </div>
                  <div>
                    <p className="text-xs text-muted-foreground">Total Tasks</p>
                    <p className="text-lg font-bold">{reportData.summary?.total_tasks || 0}</p>
                  </div>
                  <div>
                    <p className="text-xs text-muted-foreground">Completed</p>
                    <p className="text-lg font-bold text-green-600">{reportData.summary?.total_completed || 0}</p>
                  </div>
                </div>
              </>
            )}

            {/* Task Completion Rates Report */}
            {selectedReport === "task-completion" && reportData.projects && (
              <>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Project</TableHead>
                      <TableHead className="text-right">Total Tasks</TableHead>
                      <TableHead className="text-right">Completed</TableHead>
                      <TableHead className="text-right">Completion Rate</TableHead>
                      <TableHead className="text-right">Avg Time to Complete</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {reportData.projects.map((project, idx) => (
                      <TableRow key={idx}>
                        <TableCell className="font-medium">{project.name || "Unknown"}</TableCell>
                        <TableCell className="text-right">{project.total_tasks || 0}</TableCell>
                        <TableCell className="text-right text-green-600">{project.completed_tasks || 0}</TableCell>
                        <TableCell className="text-right">
                          <div className="flex items-center justify-end gap-2">
                            <Progress value={project.completion_rate || 0} className="h-2 w-16" />
                            <span className="font-mono">{project.completion_rate?.toFixed(1) || 0}%</span>
                          </div>
                        </TableCell>
                        <TableCell className="text-right">{project.avg_completion_time || "N/A"}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </>
            )}

            {/* Team Productivity Report */}
            {selectedReport === "team-productivity" && reportData.grouped_data && (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Team Member</TableHead>
                    <TableHead className="text-right">Time Logged</TableHead>
                    <TableHead className="text-right">Tasks Completed</TableHead>
                    <TableHead className="text-right">Avg Hours/Task</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {reportData.grouped_data.map((row, idx) => (
                    <TableRow key={idx}>
                      <TableCell className="font-medium">{row.user_name || "Unknown"}</TableCell>
                      <TableCell className="text-right font-mono">{row.total_hours?.toFixed(2) || 0}h</TableCell>
                      <TableCell className="text-right">{row.tasks_completed || 0}</TableCell>
                      <TableCell className="text-right font-mono">{row.avg_hours_per_task?.toFixed(2) || 0}h</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}

            {/* Delays & Bottlenecks Report */}
            {selectedReport === "delays-bottlenecks" && reportData.delayed_tasks && (
              <>
                <div className="grid grid-cols-3 gap-4 mb-4">
                  <Card>
                    <CardContent className="pt-6">
                      <p className="text-xs text-muted-foreground">Total Delayed</p>
                      <p className="text-2xl font-bold text-red-600">{reportData.summary?.total_delayed || 0}</p>
                    </CardContent>
                  </Card>
                  <Card>
                    <CardContent className="pt-6">
                      <p className="text-xs text-muted-foreground">Avg Delay</p>
                      <p className="text-2xl font-bold">{reportData.summary?.avg_delay_days?.toFixed(1) || 0} days</p>
                    </CardContent>
                  </Card>
                  <Card>
                    <CardContent className="pt-6">
                      <p className="text-xs text-muted-foreground">Bottleneck Projects</p>
                      <p className="text-2xl font-bold text-orange-600">{reportData.summary?.bottleneck_count || 0}</p>
                    </CardContent>
                  </Card>
                </div>
                
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Task</TableHead>
                      <TableHead>Project</TableHead>
                      <TableHead>Due Date</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead className="text-right">Days Delayed</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {reportData.delayed_tasks.map((task, idx) => (
                      <TableRow key={idx}>
                        <TableCell className="font-medium">{task.title || "Unknown"}</TableCell>
                        <TableCell>{task.project_name || "Unknown"}</TableCell>
                        <TableCell>{task.due_date ? format(new Date(task.due_date), "MMM d, yyyy") : "N/A"}</TableCell>
                        <TableCell><Badge variant="outline">{task.status}</Badge></TableCell>
                        <TableCell className="text-right text-red-600 font-medium">{task.days_delayed || 0}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </>
            )}

            {/* Empty State */}
            {reportData && (
              (selectedReport === "time-tracking" && (!reportData.grouped_data || reportData.grouped_data.length === 0)) ||
              (selectedReport === "budget-summary" && (!reportData.budgets || reportData.budgets.length === 0)) ||
              (selectedReport === "project-progress" && (!reportData.projects || reportData.projects.length === 0)) ||
              (selectedReport === "task-completion" && (!reportData.projects || reportData.projects.length === 0)) ||
              (selectedReport === "team-productivity" && (!reportData.grouped_data || reportData.grouped_data.length === 0)) ||
              (selectedReport === "delays-bottlenecks" && (!reportData.delayed_tasks || reportData.delayed_tasks.length === 0))
            ) && (
              <div className="text-center py-12 text-muted-foreground">
                <FileText className="w-16 h-16 mx-auto mb-4 opacity-30" />
                <p className="text-lg font-medium">No data available</p>
                <p className="text-sm mt-2">Try adjusting your filters or date range</p>
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
