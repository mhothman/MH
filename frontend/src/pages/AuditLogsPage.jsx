import { useState, useEffect } from "react";
import { useAuth } from "../context/AuthContext";
import {
  getOrganizations,
  getOrganizationMembers,
  getMyPermissions,
  hasPermission,
  Permission,
} from "../api";
import {
  getAuditLogs,
  exportAuditLogs,
  getAuditActions,
  getAuditResourceTypes,
} from "../api/audit";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../components/ui/card";
import { Badge } from "../components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../components/ui/table";
import { LoadingSpinner } from "../components/ui/loading-spinner";
import { toast } from "sonner";
import {
  Shield,
  Download,
  Filter,
  RefreshCw,
  User,
  FileText,
  Edit,
  Trash2,
  Plus,
  Eye,
  Calendar,
  ChevronLeft,
  ChevronRight,
  Search,
  X,
} from "lucide-react";

const ACTION_ICONS = {
  create: Plus,
  read: Eye,
  update: Edit,
  delete: Trash2,
  login: User,
  logout: User,
  export: Download,
};

const ACTION_COLORS = {
  create: "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400",
  read: "bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400",
  update: "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400",
  delete: "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400",
  login: "bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-400",
  logout: "bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-400",
  export: "bg-indigo-100 text-indigo-800 dark:bg-indigo-900/30 dark:text-indigo-400",
};

// Helper function to format details in a friendly way
const formatDetails = (details) => {
  if (!details) return null;
  if (typeof details === "string") return details;
  if (typeof details !== "object") return String(details);
  
  // Convert object to friendly key-value pairs
  const entries = Object.entries(details);
  if (entries.length === 0) return null;
  
  return entries.map(([key, value]) => {
    // Format the key: convert snake_case to Title Case
    const formattedKey = key
      .replace(/_/g, ' ')
      .replace(/\b\w/g, c => c.toUpperCase());
    
    // Format the value
    let formattedValue = value;
    if (value === null || value === undefined) {
      formattedValue = '—';
    } else if (typeof value === 'boolean') {
      formattedValue = value ? 'Yes' : 'No';
    } else if (Array.isArray(value)) {
      formattedValue = value.length > 0 ? value.join(', ') : '—';
    } else if (typeof value === 'object') {
      formattedValue = Object.keys(value).join(', ');
    }
    
    return `${formattedKey}: ${formattedValue}`;
  }).join(' • ');
};

export default function AuditLogsPage() {
  const { user } = useAuth();
  const [loading, setLoading] = useState(true);
  const [organizations, setOrganizations] = useState([]);
  const [selectedOrg, setSelectedOrg] = useState(null);
  const [logs, setLogs] = useState([]);
  const [total, setTotal] = useState(0);
  const [actions, setActions] = useState([]);
  const [resourceTypes, setResourceTypes] = useState([]);
  const [members, setMembers] = useState([]);
  const [permissions, setPermissions] = useState([]);
  
  // Permission check helper
  const canDo = (permission) => hasPermission(permissions, permission);
  
  // Filters
  const [filters, setFilters] = useState({
    userId: "",
    action: "",
    resourceType: "",
    startDate: "",
    endDate: "",
  });
  const [showFilters, setShowFilters] = useState(false);
  
  // Pagination
  const [page, setPage] = useState(0);
  const [limit] = useState(25);
  
  // Export
  const [exporting, setExporting] = useState(false);

  useEffect(() => {
    loadInitialData();
  }, []);

  useEffect(() => {
    if (selectedOrg) {
      loadLogs();
      loadMembers();
      loadPermissions();
    }
  }, [selectedOrg, page, filters]);

  const loadInitialData = async () => {
    try {
      const [orgsData, actionsData, resourceTypesData] = await Promise.all([
        getOrganizations(),
        getAuditActions().catch(() => ({ actions: [] })),
        getAuditResourceTypes().catch(() => ({ resource_types: [] })),
      ]);
      setOrganizations(orgsData);
      setActions(actionsData.actions || []);
      setResourceTypes(resourceTypesData.resource_types || []);
      if (orgsData.length > 0) {
        setSelectedOrg(orgsData[0]);
      }
    } catch (error) {
      toast.error("Failed to load data");
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

  const loadLogs = async () => {
    if (!selectedOrg) return;
    setLoading(true);
    try {
      const data = await getAuditLogs(selectedOrg.org_id, {
        ...filters,
        limit,
        skip: page * limit,
      });
      setLogs(data.logs || []);
      setTotal(data.total || 0);
    } catch (error) {
      if (error.message.includes("not available")) {
        setLogs([]);
        toast.error("Audit logs feature not available on your plan");
      } else {
        toast.error("Failed to load audit logs");
      }
    } finally {
      setLoading(false);
    }
  };

  const loadMembers = async () => {
    try {
      const data = await getOrganizationMembers(selectedOrg.org_id);
      setMembers(data);
    } catch (error) {
      console.error("Failed to load members:", error);
    }
  };

  const handleExport = async (format) => {
    setExporting(true);
    try {
      const result = await exportAuditLogs(
        selectedOrg.org_id,
        format,
        filters.startDate || null,
        filters.endDate || null
      );

      if (format === "csv") {
        const url = URL.createObjectURL(result);
        const a = document.createElement("a");
        a.href = url;
        a.download = `audit_logs_${selectedOrg.org_id}_${new Date().toISOString().split("T")[0]}.csv`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
      } else {
        // JSON - download as file
        const blob = new Blob([JSON.stringify(result, null, 2)], { type: "application/json" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `audit_logs_${selectedOrg.org_id}_${new Date().toISOString().split("T")[0]}.json`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
      }

      toast.success(`Exported ${format.toUpperCase()} successfully`);
    } catch (error) {
      toast.error("Failed to export audit logs");
    } finally {
      setExporting(false);
    }
  };

  const clearFilters = () => {
    setFilters({
      userId: "",
      action: "",
      resourceType: "",
      startDate: "",
      endDate: "",
    });
    setPage(0);
  };

  const hasActiveFilters = Object.values(filters).some(Boolean);
  const totalPages = Math.ceil(total / limit);

  const getMemberName = (userId) => {
    const member = members.find(m => m.user_id === userId);
    return member?.name || userId;
  };

  if (loading && !selectedOrg) {
    return (
      <div className="flex items-center justify-center h-[60vh]">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="audit-logs-page">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <Shield className="h-6 w-6 text-blue-500" />
            Audit Logs
          </h1>
          <p className="text-muted-foreground">
            Track all actions and changes in your organization
          </p>
        </div>
        <div className="flex items-center gap-2">
          {organizations.length > 1 && (
            <Select value={selectedOrg?.org_id} onValueChange={(val) => { setSelectedOrg(organizations.find(o => o.org_id === val)); setPage(0); }}>
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
          <Button variant="outline" onClick={() => setShowFilters(!showFilters)} data-testid="toggle-filters-btn">
            <Filter className="h-4 w-4 mr-2" />
            Filters
            {hasActiveFilters && <Badge variant="secondary" className="ml-2">{Object.values(filters).filter(Boolean).length}</Badge>}
          </Button>
          <Button variant="outline" onClick={() => loadLogs()}>
            <RefreshCw className="h-4 w-4" />
          </Button>
          {canDo(Permission.AUDIT_EXPORT) && (
            <Select onValueChange={handleExport} disabled={exporting}>
              <SelectTrigger className="w-32" data-testid="export-select">
                <Download className="h-4 w-4 mr-2" />
                Export
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="csv">Export CSV</SelectItem>
                <SelectItem value="json">Export JSON</SelectItem>
              </SelectContent>
            </Select>
          )}
        </div>
      </div>

      {/* Filters Panel */}
      {showFilters && (
        <Card>
          <CardContent className="pt-4">
            <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
              <div>
                <Label className="text-xs">User</Label>
                <Select value={filters.userId || "all"} onValueChange={(val) => { setFilters(prev => ({ ...prev, userId: val === "all" ? "" : val })); setPage(0); }}>
                  <SelectTrigger>
                    <SelectValue placeholder="All users" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All users</SelectItem>
                    {members.map((m) => (
                      <SelectItem key={m.user_id} value={m.user_id}>{m.name}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label className="text-xs">Action</Label>
                <Select value={filters.action || "all"} onValueChange={(val) => { setFilters(prev => ({ ...prev, action: val === "all" ? "" : val })); setPage(0); }}>
                  <SelectTrigger>
                    <SelectValue placeholder="All actions" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All actions</SelectItem>
                    {actions.map((a) => (
                      <SelectItem key={a} value={a}>{a}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label className="text-xs">Resource Type</Label>
                <Select value={filters.resourceType || "all"} onValueChange={(val) => { setFilters(prev => ({ ...prev, resourceType: val === "all" ? "" : val })); setPage(0); }}>
                  <SelectTrigger>
                    <SelectValue placeholder="All types" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All types</SelectItem>
                    {resourceTypes.map((rt) => (
                      <SelectItem key={rt} value={rt}>{rt}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label className="text-xs">Start Date</Label>
                <Input
                  type="date"
                  value={filters.startDate}
                  onChange={(e) => { setFilters(prev => ({ ...prev, startDate: e.target.value })); setPage(0); }}
                />
              </div>
              <div>
                <Label className="text-xs">End Date</Label>
                <Input
                  type="date"
                  value={filters.endDate}
                  onChange={(e) => { setFilters(prev => ({ ...prev, endDate: e.target.value })); setPage(0); }}
                />
              </div>
            </div>
            {hasActiveFilters && (
              <div className="mt-3 flex justify-end">
                <Button variant="ghost" size="sm" onClick={clearFilters}>
                  <X className="h-3 w-3 mr-1" />
                  Clear filters
                </Button>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Stats Summary */}
      <div className="grid grid-cols-4 gap-4">
        <Card>
          <CardContent className="pt-4">
            <div className="text-2xl font-bold">{total}</div>
            <p className="text-xs text-muted-foreground">Total Events</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4">
            <div className="text-2xl font-bold text-green-600">
              {logs.filter(l => l.action === "create").length}
            </div>
            <p className="text-xs text-muted-foreground">Created (this page)</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4">
            <div className="text-2xl font-bold text-yellow-600">
              {logs.filter(l => l.action === "update").length}
            </div>
            <p className="text-xs text-muted-foreground">Updated (this page)</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4">
            <div className="text-2xl font-bold text-red-600">
              {logs.filter(l => l.action === "delete").length}
            </div>
            <p className="text-xs text-muted-foreground">Deleted (this page)</p>
          </CardContent>
        </Card>
      </div>

      {/* Logs Table */}
      <Card>
        <CardContent className="p-0">
          {loading ? (
            <div className="flex justify-center py-12">
              <LoadingSpinner />
            </div>
          ) : logs.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12">
              <Shield className="h-12 w-12 text-muted-foreground mb-4" />
              <h3 className="text-lg font-medium mb-2">No audit logs found</h3>
              <p className="text-muted-foreground text-center">
                {hasActiveFilters ? "Try adjusting your filters" : "Activity will appear here"}
              </p>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Timestamp</TableHead>
                  <TableHead>User</TableHead>
                  <TableHead>Action</TableHead>
                  <TableHead>Resource</TableHead>
                  <TableHead>Resource ID</TableHead>
                  <TableHead>Details</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {logs.map((log, index) => {
                  const ActionIcon = ACTION_ICONS[log.action] || FileText;
                  const actionColor = ACTION_COLORS[log.action] || ACTION_COLORS.read;
                  return (
                    <TableRow key={log.log_id || index} data-testid={`audit-log-${log.log_id || index}`}>
                      <TableCell className="text-xs">
                        <div className="flex items-center gap-1">
                          <Calendar className="h-3 w-3 text-muted-foreground" />
                          {new Date(log.timestamp).toLocaleString()}
                        </div>
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          <User className="h-4 w-4 text-muted-foreground" />
                          <span className="text-sm">{getMemberName(log.user_id)}</span>
                        </div>
                      </TableCell>
                      <TableCell>
                        <Badge className={`${actionColor} font-normal`}>
                          <ActionIcon className="h-3 w-3 mr-1" />
                          {log.action}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-sm">{log.resource_type}</TableCell>
                      <TableCell>
                        <code className="text-xs bg-muted px-1 py-0.5 rounded">
                          {log.resource_id?.slice(0, 16)}...
                        </code>
                      </TableCell>
                      <TableCell className="max-w-[250px]">
                        {log.details && (
                          <span className="text-xs text-muted-foreground block" title={typeof log.details === "object" ? JSON.stringify(log.details, null, 2) : log.details}>
                            {formatDetails(log.details)}
                          </span>
                        )}
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          )}
        </CardContent>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between p-4 border-t">
            <p className="text-sm text-muted-foreground">
              Showing {page * limit + 1} - {Math.min((page + 1) * limit, total)} of {total}
            </p>
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setPage(p => Math.max(0, p - 1))}
                disabled={page === 0}
              >
                <ChevronLeft className="h-4 w-4" />
                Previous
              </Button>
              <span className="text-sm">
                Page {page + 1} of {totalPages}
              </span>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setPage(p => Math.min(totalPages - 1, p + 1))}
                disabled={page >= totalPages - 1}
              >
                Next
                <ChevronRight className="h-4 w-4" />
              </Button>
            </div>
          </div>
        )}
      </Card>
    </div>
  );
}
