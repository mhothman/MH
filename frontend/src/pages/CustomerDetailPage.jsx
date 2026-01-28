import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { getCustomer, updateCustomer } from "../api/customers";
import { getProjects } from "../api/projects";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Textarea } from "../components/ui/textarea";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Badge } from "../components/ui/badge";
import { Progress } from "../components/ui/progress";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../components/ui/tabs";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "../components/ui/dialog";
import { LoadingSpinner } from "../components/ui/loading-spinner";
import { toast } from "sonner";
import {
  ArrowLeft,
  Mail,
  Phone,
  Building2,
  MapPin,
  Calendar,
  FolderKanban,
  Pencil,
  FileText,
  Clock,
  CheckCircle2,
  Users,
  TrendingUp,
} from "lucide-react";
import { format, formatDistanceToNow } from "date-fns";

export default function CustomerDetailPage() {
  const { customerId } = useParams();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [customer, setCustomer] = useState(null);
  const [projects, setProjects] = useState([]);
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [formData, setFormData] = useState({
    name: "",
    email: "",
    contact: "",
    company: "",
    address: "",
    notes: "",
  });

  useEffect(() => {
    loadData();
  }, [customerId]);

  const loadData = async () => {
    try {
      const [customerData, projectsData] = await Promise.all([
        getCustomer(customerId),
        getProjects(),
      ]);
      setCustomer(customerData);
      // Filter projects for this customer
      const customerProjects = projectsData.filter(p => p.customer_id === customerId);
      setProjects(customerProjects);
      setFormData({
        name: customerData.name || "",
        email: customerData.email || "",
        contact: customerData.phone || customerData.contact || "",  // Backend returns 'phone'
        company: customerData.company || "",
        address: customerData.address || "",
        notes: customerData.notes || "",
      });
    } catch (error) {
      console.error("Failed to load customer:", error);
      toast.error("Failed to load customer");
    } finally {
      setLoading(false);
    }
  };

  const handleUpdate = async () => {
    if (!formData.name.trim()) {
      toast.error("Customer name is required");
      return;
    }

    setSaving(true);
    try {
      const updated = await updateCustomer(customerId, formData);
      setCustomer(updated);
      setEditDialogOpen(false);
      toast.success("Customer updated successfully");
    } catch (error) {
      toast.error(error.message || "Failed to update customer");
    } finally {
      setSaving(false);
    }
  };

  const getProjectProgress = (project) => {
    if (!project.task_count || project.task_count === 0) return 0;
    return Math.round((project.completed_tasks / project.task_count) * 100);
  };

  const getStatusColor = (status) => {
    switch (status) {
      case "active": return "bg-green-500";
      case "completed": return "bg-blue-500";
      case "on_hold": return "bg-yellow-500";
      default: return "bg-slate-500";
    }
  };

  // Calculate stats
  const totalProjects = projects.length;
  const activeProjects = projects.filter(p => p.status === "active").length;
  const completedProjects = projects.filter(p => p.status === "completed").length;
  const totalTasks = projects.reduce((sum, p) => sum + (p.task_count || 0), 0);
  const completedTasks = projects.reduce((sum, p) => sum + (p.completed_tasks || 0), 0);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-[60vh]">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  if (!customer) {
    return (
      <div className="text-center py-12">
        <h2 className="text-xl font-semibold">Customer not found</h2>
        <Button variant="outline" className="mt-4" onClick={() => navigate("/customers")}>
          Back to Customers
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-fade-in" data-testid="customer-detail-page">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={() => navigate("/customers")} data-testid="back-btn">
            <ArrowLeft className="w-5 h-5" />
          </Button>
          <div className="w-14 h-14 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white font-bold text-xl">
            {customer.name.charAt(0).toUpperCase()}
          </div>
          <div>
            <h1 className="font-heading text-2xl font-bold tracking-tight">{customer.name}</h1>
            {customer.company && (
              <p className="text-muted-foreground flex items-center gap-1">
                <Building2 className="w-4 h-4" />
                {customer.company}
              </p>
            )}
          </div>
        </div>
        <Button variant="outline" onClick={() => setEditDialogOpen(true)} data-testid="edit-customer-btn">
          <Pencil className="w-4 h-4 mr-2" />
          Edit Customer
        </Button>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Total Projects</p>
                <p className="text-2xl font-bold">{totalProjects}</p>
              </div>
              <div className="p-3 rounded-full bg-blue-100 dark:bg-blue-900/30">
                <FolderKanban className="w-5 h-5 text-blue-600" />
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Active</p>
                <p className="text-2xl font-bold text-green-600">{activeProjects}</p>
              </div>
              <div className="p-3 rounded-full bg-green-100 dark:bg-green-900/30">
                <TrendingUp className="w-5 h-5 text-green-600" />
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Completed</p>
                <p className="text-2xl font-bold text-blue-600">{completedProjects}</p>
              </div>
              <div className="p-3 rounded-full bg-blue-100 dark:bg-blue-900/30">
                <CheckCircle2 className="w-5 h-5 text-blue-600" />
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Tasks Done</p>
                <p className="text-2xl font-bold">{completedTasks}/{totalTasks}</p>
              </div>
              <div className="p-3 rounded-full bg-purple-100 dark:bg-purple-900/30">
                <CheckCircle2 className="w-5 h-5 text-purple-600" />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Tabs */}
      <Tabs defaultValue="projects">
        <TabsList>
          <TabsTrigger value="projects">
            <FolderKanban className="w-4 h-4 mr-2" />
            Projects ({totalProjects})
          </TabsTrigger>
          <TabsTrigger value="info">
            <FileText className="w-4 h-4 mr-2" />
            Information
          </TabsTrigger>
        </TabsList>

        {/* Projects Tab */}
        <TabsContent value="projects" className="mt-6">
          {projects.length === 0 ? (
            <Card>
              <CardContent className="flex flex-col items-center justify-center py-12">
                <FolderKanban className="w-12 h-12 text-muted-foreground mb-4" />
                <p className="text-muted-foreground mb-4">No projects linked to this customer</p>
                <Button onClick={() => navigate("/projects")}>
                  Create Project
                </Button>
              </CardContent>
            </Card>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {projects.map((project) => (
                <Card 
                  key={project.project_id} 
                  className="hover:shadow-md transition-shadow cursor-pointer"
                  onClick={() => navigate(`/projects/${project.project_id}`)}
                  data-testid={`project-card-${project.project_id}`}
                >
                  <CardContent className="pt-6">
                    <div className="flex items-start justify-between mb-3">
                      <div className="flex items-center gap-3">
                        <div
                          className="w-10 h-10 rounded-lg flex items-center justify-center text-white font-bold"
                          style={{ backgroundColor: project.color || "#3B82F6" }}
                        >
                          {project.name.charAt(0).toUpperCase()}
                        </div>
                        <div>
                          <h3 className="font-semibold">{project.name}</h3>
                          <Badge 
                            variant="secondary" 
                            className={`text-xs text-white ${getStatusColor(project.status)}`}
                          >
                            {project.status}
                          </Badge>
                        </div>
                      </div>
                    </div>
                    
                    {project.description && (
                      <p className="text-sm text-muted-foreground line-clamp-2 mb-3">
                        {project.description}
                      </p>
                    )}

                    <div className="space-y-2">
                      <div className="flex items-center justify-between text-sm">
                        <span className="text-muted-foreground">Progress</span>
                        <span className="font-medium">{getProjectProgress(project)}%</span>
                      </div>
                      <Progress value={getProjectProgress(project)} className="h-2" />
                    </div>

                    <div className="flex items-center justify-between mt-4 text-xs text-muted-foreground">
                      <span className="flex items-center gap-1">
                        <CheckCircle2 className="w-3 h-3" />
                        {project.completed_tasks || 0}/{project.task_count || 0} tasks
                      </span>
                      {project.end_date && (
                        <span className="flex items-center gap-1">
                          <Calendar className="w-3 h-3" />
                          Due {format(new Date(project.end_date), "MMM d")}
                        </span>
                      )}
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </TabsContent>

        {/* Information Tab */}
        <TabsContent value="info" className="mt-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Contact Information</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded-lg bg-muted">
                    <Mail className="w-4 h-4 text-muted-foreground" />
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Email</p>
                    {customer.email ? (
                      <a href={`mailto:${customer.email}`} className="text-blue-600 hover:underline">
                        {customer.email}
                      </a>
                    ) : (
                      <p className="text-muted-foreground">Not provided</p>
                    )}
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded-lg bg-muted">
                    <Phone className="w-4 h-4 text-muted-foreground" />
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Contact Number</p>
                    {(customer.phone || customer.contact) ? (
                      <a href={`tel:${customer.phone || customer.contact}`} className="hover:underline">
                        {customer.phone || customer.contact}
                      </a>
                    ) : (
                      <p className="text-muted-foreground">Not provided</p>
                    )}
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded-lg bg-muted">
                    <Building2 className="w-4 h-4 text-muted-foreground" />
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Company</p>
                    <p>{customer.company || "Not provided"}</p>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded-lg bg-muted">
                    <MapPin className="w-4 h-4 text-muted-foreground" />
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">Address</p>
                    <p>{customer.address || "Not provided"}</p>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Additional Details</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <p className="text-sm text-muted-foreground mb-1">Notes</p>
                  <p className="text-sm bg-muted/50 rounded-lg p-3">
                    {customer.notes || "No notes added"}
                  </p>
                </div>
                <div className="pt-4 border-t space-y-2">
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-muted-foreground flex items-center gap-1">
                      <Calendar className="w-4 h-4" />
                      Created
                    </span>
                    <span>{format(new Date(customer.created_at), "MMM d, yyyy 'at' h:mm a")}</span>
                  </div>
                  {customer.updated_at && customer.updated_at !== customer.created_at && (
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-muted-foreground flex items-center gap-1">
                        <Clock className="w-4 h-4" />
                        Last Updated
                      </span>
                      <span>{formatDistanceToNow(new Date(customer.updated_at), { addSuffix: true })}</span>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>
      </Tabs>

      {/* Edit Dialog */}
      <Dialog open={editDialogOpen} onOpenChange={setEditDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Edit Customer</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 pt-4">
            <div className="space-y-2">
              <Label htmlFor="name">Name *</Label>
              <Input
                id="name"
                placeholder="Customer name"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="email">Email</Label>
                <Input
                  id="email"
                  type="email"
                  placeholder="email@example.com"
                  value={formData.email}
                  onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="contact">Contact Number</Label>
                <Input
                  id="contact"
                  placeholder="+1 234 567 8900"
                  value={formData.contact}
                  onChange={(e) => setFormData({ ...formData, contact: e.target.value })}
                />
              </div>
            </div>
            <div className="space-y-2">
              <Label htmlFor="company">Company</Label>
              <Input
                id="company"
                placeholder="Company name"
                value={formData.company}
                onChange={(e) => setFormData({ ...formData, company: e.target.value })}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="address">Address</Label>
              <Input
                id="address"
                placeholder="Address"
                value={formData.address}
                onChange={(e) => setFormData({ ...formData, address: e.target.value })}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="notes">Notes</Label>
              <Textarea
                id="notes"
                placeholder="Additional notes..."
                value={formData.notes}
                onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
              />
            </div>
            <div className="flex justify-end gap-2 pt-4">
              <Button variant="outline" onClick={() => setEditDialogOpen(false)}>
                Cancel
              </Button>
              <Button onClick={handleUpdate} disabled={saving}>
                {saving ? <LoadingSpinner size="sm" /> : "Save Changes"}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
