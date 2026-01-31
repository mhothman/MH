import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useAppData } from "../context/AppDataContext";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Badge } from "../components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../components/ui/table";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "../components/ui/dialog";
import { Label } from "../components/ui/label";
import { LoadingSpinner } from "../components/ui/loading-spinner";
import { UserPlus, Search, Users, Briefcase, Phone, Mail, CreditCard } from "lucide-react";
import { toast } from "sonner";

export default function SeasonalEmployeesPage() {
  const navigate = useNavigate();
  const { currentOrgId } = useAppData();
  const [employees, setEmployees] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  const [dialogOpen, setDialogOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [formData, setFormData] = useState({
    first_name: "",
    second_name: "",
    third_name: "",
    national_id: "",
    profession: "",
    mobile_number: "",
    email: ""
  });

  useEffect(() => {
    if (currentOrgId) {
      loadEmployees();
    }
  }, [currentOrgId]);

  const loadEmployees = async () => {
    setLoading(true);
    try {
      const API_URL = process.env.REACT_APP_BACKEND_URL;
      const token = localStorage.getItem('proflow_token');
      
      const response = await fetch(
        `${API_URL}/api/seasonal-employees/org/${currentOrgId}`,
        { headers: { 'Authorization': `Bearer ${token}` } }
      );
      
      if (!response.ok) throw new Error('Failed to load seasonal employees');
      
      const data = await response.json();
      setEmployees(data);
    } catch (error) {
      toast.error(error.message || 'Failed to load seasonal employees');
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async (e) => {
    e.preventDefault();
    setSaving(true);
    
    try {
      const API_URL = process.env.REACT_APP_BACKEND_URL;
      const token = localStorage.getItem('proflow_token');
      
      const response = await fetch(
        `${API_URL}/api/seasonal-employees/?org_id=${currentOrgId}`,
        {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify(formData)
        }
      );
      
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to create employee');
      }
      
      toast.success('Seasonal employee created successfully');
      setDialogOpen(false);
      setFormData({
        first_name: "",
        second_name: "",
        third_name: "",
        national_id: "",
        profession: "",
        mobile_number: "",
        email: ""
      });
      loadEmployees();
    } catch (error) {
      toast.error(error.message);
    } finally {
      setSaving(false);
    }
  };

  const filteredEmployees = employees.filter(emp =>
    emp.full_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    emp.national_id.includes(searchTerm) ||
    emp.profession.toLowerCase().includes(searchTerm.toLowerCase())
  );

  if (loading) {
    return (
      <div className="flex items-center justify-center h-[60vh]">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Users className="w-8 h-8 text-orange-600" />
          <div>
            <h1 className="font-heading text-2xl sm:text-3xl font-bold tracking-tight">
              Seasonal Employees
            </h1>
            <p className="text-muted-foreground mt-1">
              Manage temporary workers without system access
            </p>
          </div>
        </div>
        <Button onClick={() => setDialogOpen(true)}>
          <UserPlus className="w-4 h-4 mr-2" />
          Add Seasonal Employee
        </Button>
      </div>

      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>All Seasonal Employees ({employees.length})</CardTitle>
            <div className="relative">
              <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search by name, ID, or profession..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-8 w-80"
              />
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {filteredEmployees.length === 0 ? (
            <div className="text-center py-12 text-muted-foreground">
              <Users className="w-16 h-16 mx-auto mb-4 opacity-30" />
              <p className="text-lg font-medium">No seasonal employees found</p>
              <p className="text-sm mt-2">Add your first seasonal employee to get started</p>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>National ID</TableHead>
                  <TableHead>Profession</TableHead>
                  <TableHead>Contact</TableHead>
                  <TableHead className="text-right">Projects</TableHead>
                  <TableHead className="text-right">Days Worked</TableHead>
                  <TableHead className="text-right">Total Cost</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredEmployees.map((emp) => (
                  <TableRow key={emp.employee_id} className="cursor-pointer hover:bg-accent/50">
                    <TableCell className="font-medium">{emp.full_name}</TableCell>
                    <TableCell className="font-mono text-sm">{emp.national_id}</TableCell>
                    <TableCell>
                      <Badge variant="outline">{emp.profession}</Badge>
                    </TableCell>
                    <TableCell>
                      <div className="text-sm">
                        <p className="flex items-center gap-1">
                          <Phone className="w-3 h-3" />
                          {emp.mobile_number}
                        </p>
                        {emp.email && (
                          <p className="flex items-center gap-1 text-muted-foreground">
                            <Mail className="w-3 h-3" />
                            {emp.email}
                          </p>
                        )}
                      </div>
                    </TableCell>
                    <TableCell className="text-right">{emp.total_projects || 0}</TableCell>
                    <TableCell className="text-right">{emp.total_days_worked || 0}</TableCell>
                    <TableCell className="text-right font-mono">
                      E£{emp.total_cost?.toLocaleString() || 0}
                    </TableCell>
                    <TableCell className="text-right">
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => navigate(`/seasonal-employees/${emp.employee_id}`)}
                      >
                        View Details
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Create Employee Dialog */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="sm:max-w-[600px]">
          <DialogHeader>
            <DialogTitle>Add Seasonal Employee</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleCreate} className="space-y-4">
            <div className="grid grid-cols-3 gap-4">
              <div className="space-y-2">
                <Label>First Name *</Label>
                <Input
                  value={formData.first_name}
                  onChange={(e) => setFormData({ ...formData, first_name: e.target.value })}
                  required
                />
              </div>
              <div className="space-y-2">
                <Label>Second Name *</Label>
                <Input
                  value={formData.second_name}
                  onChange={(e) => setFormData({ ...formData, second_name: e.target.value })}
                  required
                />
              </div>
              <div className="space-y-2">
                <Label>Third Name *</Label>
                <Input
                  value={formData.third_name}
                  onChange={(e) => setFormData({ ...formData, third_name: e.target.value })}
                  required
                />
              </div>
            </div>
            
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>National ID *</Label>
                <Input
                  value={formData.national_id}
                  onChange={(e) => setFormData({ ...formData, national_id: e.target.value })}
                  placeholder="e.g., 1234567890"
                  required
                />
              </div>
              <div className="space-y-2">
                <Label>Profession *</Label>
                <Input
                  value={formData.profession}
                  onChange={(e) => setFormData({ ...formData, profession: e.target.value })}
                  placeholder="e.g., Carpenter, Electrician"
                  required
                />
              </div>
            </div>
            
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Mobile Number *</Label>
                <Input
                  value={formData.mobile_number}
                  onChange={(e) => setFormData({ ...formData, mobile_number: e.target.value })}
                  placeholder="+20 123 456 7890"
                  required
                />
              </div>
              <div className="space-y-2">
                <Label>Email (Optional)</Label>
                <Input
                  type="email"
                  value={formData.email}
                  onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                  placeholder="optional@example.com"
                />
              </div>
            </div>

            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setDialogOpen(false)}>
                Cancel
              </Button>
              <Button type="submit" disabled={saving}>
                {saving ? <LoadingSpinner size="sm" className="mr-2" /> : null}
                Create Employee
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
