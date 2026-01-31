import { useState } from "react";
import { useAppData } from "../context/AppDataContext";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Label } from "../components/ui/label";
import { Input } from "../components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../components/ui/select";
import { FileDown, FileText, Calendar, Users, DollarSign, TrendingUp } from "lucide-react";
import { toast } from "sonner";

const REPORT_TYPES = [
  { id: "time-tracking", label: "Time Tracking Report", icon: Calendar, description: "Detailed time logs and summaries" },
  { id: "budget-summary", label: "Budget Summary Report", icon: DollarSign, description: "Budget status across projects" },
  { id: "project-progress", label: "Project Progress Report", icon: TrendingUp, description: "Project completion metrics" },
];

export default function CustomReportsPage() {
  const { currentOrgId } = useAppData();
  const [selectedReport, setSelectedReport] = useState("time-tracking");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [groupBy, setGroupBy] = useState("project");
  const [loading, setLoading] = useState(false);

  const handleExport = async (format) => {
    if (!currentOrgId) {
      toast.error("Please select an organization");
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
      
      url += `&export_format=${format}`;
      
      const response = await fetch(url, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      
      if (!response.ok) throw new Error('Export failed');
      
      // Download file
      const blob = await response.blob();
      const downloadUrl = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = downloadUrl;
      a.download = `report_${selectedReport}_${new Date().toISOString().split('T')[0]}.${format}`;
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
    try {
      const API_URL = process.env.REACT_APP_BACKEND_URL;
      const token = localStorage.getItem('proflow_token');
      
      let url = `${API_URL}/api/custom-reports/${selectedReport}?org_id=${currentOrgId}`;
      
      if (selectedReport === "time-tracking") {
        if (startDate) url += `&start_date=${startDate}`;
        if (endDate) url += `&end_date=${endDate}`;
        url += `&group_by=${groupBy}`;
      }
      
      const response = await fetch(url, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      
      if (!response.ok) throw new Error('Failed to generate report');
      
      const data = await response.json();
      console.log('Report Preview:', data);
      toast.success("Report generated - check console for preview");
    } catch (error) {
      toast.error(error.message || "Failed to generate report");
    } finally {
      setLoading(false);
    }
  };

  const selectedReportConfig = REPORT_TYPES.find(r => r.id === selectedReport);
  const ReportIcon = selectedReportConfig?.icon || FileText;

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center gap-3">
        <FileText className="w-8 h-8 text-blue-600" />
        <div>
          <h1 className="font-heading text-2xl sm:text-3xl font-bold tracking-tight">
            Custom Reports
          </h1>
          <p className="text-muted-foreground mt-1">
            Generate and export custom reports
          </p>
        </div>
      </div>

      <div className="grid lg:grid-cols-3 gap-6">
        {/* Report Selection */}
        <Card className="lg:col-span-1">
          <CardHeader>
            <CardTitle className="text-lg">Report Type</CardTitle>
            <CardDescription>Choose the report to generate</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {REPORT_TYPES.map((report) => {
              const Icon = report.icon;
              return (
                <button
                  key={report.id}
                  onClick={() => setSelectedReport(report.id)}
                  className={`w-full p-3 text-left rounded-lg border-2 transition-all ${
                    selectedReport === report.id
                      ? "border-primary bg-primary/5"
                      : "border-border hover:border-primary/50"
                  }`}
                >
                  <div className="flex items-start gap-3">
                    <Icon className="w-5 h-5 mt-0.5 text-primary" />
                    <div>
                      <p className="font-medium">{report.label}</p>
                      <p className="text-xs text-muted-foreground mt-1">{report.description}</p>
                    </div>
                  </div>
                </button>
              );
            })}
          </CardContent>
        </Card>

        {/* Report Configuration */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <div className="flex items-center gap-2">
              <ReportIcon className="w-5 h-5 text-primary" />
              <CardTitle className="text-lg">{selectedReportConfig?.label}</CardTitle>
            </div>
            <CardDescription>{selectedReportConfig?.description}</CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* Filters */}
            {selectedReport === "time-tracking" && (
              <div className="space-y-4">
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
              </div>
            )}

            {/* Actions */}
            <div className="flex gap-3 pt-4 border-t">
              <Button onClick={handlePreview} disabled={loading} variant="outline">
                Preview
              </Button>
              <Button onClick={() => handleExport('csv')} disabled={loading}>
                <FileDown className="w-4 h-4 mr-2" />
                Export CSV
              </Button>
              <Button onClick={() => handleExport('json')} disabled={loading} variant="outline">
                <FileDown className="w-4 h-4 mr-2" />
                Export JSON
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
