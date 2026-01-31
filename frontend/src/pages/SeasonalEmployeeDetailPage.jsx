import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Badge } from "../components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../components/ui/tabs";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "../components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../components/ui/select";
import { LoadingSpinner } from "../components/ui/loading-spinner";
import { useAppData } from "../context/AppDataContext";
import { 
  ArrowLeft, 
  User, 
  Briefcase, 
  Phone, 
  Mail, 
  CreditCard, 
  Calendar,
  Clock,
  Plus,
  DollarSign,
  CheckCircle
} from "lucide-react";
import { toast } from "sonner";
import { format } from "date-fns";

export default function SeasonalEmployeeDetailPage() {
  const { employeeId } = useParams();
  const navigate = useNavigate();
  const { projects, currentOrgId } = useAppData();
  const [employee, setEmployee] = useState(null);
  const [assignments, setAssignments] = useState([]);
  const [selectedAssignment, setSelectedAssignment] = useState(null);
  const [attendance, setAttendance] = useState([]);
  const [loading, setLoading] = useState(true);
  const [assignDialog, setAssignDialog] = useState(false);
  const [attendanceDialog, setAttendanceDialog] = useState(false);
  const [assignForm, setAssignForm] = useState({
    project_id: "",
    day_rate: "",
    start_date: "",
    end_date: ""
  });
  const [attendanceForm, setAttendanceForm] = useState({
    work_date: "",
    time_in: "08:00",
    time_out: "16:00"
  });
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (employeeId) {
      loadEmployee();
      loadAssignments();
    }
  }, [employeeId]);

  const loadEmployee = async () => {
    setLoading(true);
    try {
      const API_URL = process.env.REACT_APP_BACKEND_URL;
      const token = localStorage.getItem('proflow_token');
      
      const response = await fetch(
        `${API_URL}/api/seasonal-employees/${employeeId}`,
        { headers: { 'Authorization': `Bearer ${token}` } }
      );
      
      if (!response.ok) throw new Error('Failed to load employee');
      
      const data = await response.json();
      setEmployee(data);
    } catch (error) {
      toast.error(error.message || 'Failed to load employee');
      navigate('/seasonal-employees');
    } finally {
      setLoading(false);
    }
  };

  const loadAssignments = async () => {
    try {
      const API_URL = process.env.REACT_APP_BACKEND_URL;
      const token = localStorage.getItem('proflow_token');
      
      const response = await fetch(
        `${API_URL}/api/seasonal-employees/assignments/employee/${employeeId}`,
        { headers: { 'Authorization': `Bearer ${token}` } }
      );
      
      if (!response.ok) throw new Error('Failed to load assignments');
      
      const data = await response.json();
      setAssignments(data);
    } catch (error) {
      console.error('Failed to load assignments:', error);
    }
  };

  const loadAttendance = async (assignmentId) => {
    try {
      const API_URL = process.env.REACT_APP_BACKEND_URL;
      const token = localStorage.getItem('proflow_token');
      
      const response = await fetch(
        `${API_URL}/api/seasonal-employees/attendance/assignment/${assignmentId}`,
        { headers: { 'Authorization': `Bearer ${token}` } }
      );
      
      if (!response.ok) throw new Error('Failed to load attendance');
      
      const data = await response.json();
      setAttendance(data);
    } catch (error) {
      console.error('Failed to load attendance:', error);
    }
  };

  const handleAssignProject = async (e) => {
    e.preventDefault();
    setSaving(true);
    
    try {
      const API_URL = process.env.REACT_APP_BACKEND_URL;
      const token = localStorage.getItem('proflow_token');
      
      const response = await fetch(
        `${API_URL}/api/seasonal-employees/assignments`,
        {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            seasonal_employee_id: employeeId,
            ...assignForm
          })
        }
      );
      
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to assign project');
      }
      
      toast.success('Employee assigned to project successfully');
      setAssignDialog(false);
      setAssignForm({
        project_id: "",
        day_rate: "",
        start_date: "",
        end_date: ""
      });
      loadAssignments();
      loadEmployee();
    } catch (error) {
      toast.error(error.message);
    } finally {
      setSaving(false);
    }
  };

  const handleRecordAttendance = async (e) => {
    e.preventDefault();
    if (!selectedAssignment) return;
    
    setSaving(true);
    
    try {
      const API_URL = process.env.REACT_APP_BACKEND_URL;
      const token = localStorage.getItem('proflow_token');
      
      const response = await fetch(
        `${API_URL}/api/seasonal-employees/attendance`,
        {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            seasonal_employee_project_id: selectedAssignment.assignment_id,
            ...attendanceForm
          })
        }
      );
      
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to record attendance');
      }
      
      toast.success('Attendance recorded successfully');
      setAttendanceDialog(false);
      setAttendanceForm({
        work_date: "",
        time_in: "08:00",
        time_out: "16:00"
      });
      loadAttendance(selectedAssignment.assignment_id);
      loadAssignments();
      loadEmployee();
    } catch (error) {
      toast.error(error.message);
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-[60vh]">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  if (!employee) {
    return null;
  }

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={() => navigate('/seasonal-employees')}>
            <ArrowLeft className="w-5 h-5" />
          </Button>
          <div>
            <h1 className="font-heading text-2xl sm:text-3xl font-bold tracking-tight">
              {employee.full_name}
            </h1>
            <p className="text-muted-foreground mt-1 flex items-center gap-2">
              <Briefcase className="w-4 h-4" />
              {employee.profession}
            </p>
          </div>
        </div>
        <Button onClick={() => setAssignDialog(true)}>
          <Plus className="w-4 h-4 mr-2" />
          Assign to Project
        </Button>
      </div>

      {/* Employee Info Card */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Employee Information</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div>
              <p className="text-xs text-muted-foreground mb-1">National ID</p>
              <p className="font-mono font-medium">{employee.national_id}</p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground mb-1">Mobile</p>
              <p className="flex items-center gap-1">
                <Phone className="w-3 h-3" />
                {employee.mobile_number}
              </p>
            </div>
            {employee.email && (
              <div>
                <p className="text-xs text-muted-foreground mb-1">Email</p>
                <p className="flex items-center gap-1 text-sm">
                  <Mail className="w-3 h-3" />
                  {employee.email}
                </p>
              </div>
            )}
            <div>
              <p className="text-xs text-muted-foreground mb-1">Total Cost</p>
              <p className="font-bold text-lg">E£{employee.total_cost?.toLocaleString() || 0}</p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Stats Cards */}
      <div className="grid grid-cols-3 gap-4">
        <Card>
          <CardContent className="pt-6">
            <p className="text-sm text-muted-foreground">Projects</p>
            <p className="text-2xl font-bold">{employee.total_projects || 0}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <p className="text-sm text-muted-foreground">Days Worked</p>
            <p className="text-2xl font-bold">{employee.total_days_worked || 0}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <p className="text-sm text-muted-foreground">Total Earned</p>
            <p className="text-2xl font-bold text-green-600">E£{employee.total_cost?.toLocaleString() || 0}</p>
          </CardContent>
        </Card>
      </div>

      {/* Assignments & Attendance */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Project Assignments & Attendance</CardTitle>
        </CardHeader>
        <CardContent>
          {assignments.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              <Calendar className="w-12 h-12 mx-auto mb-2 opacity-30" />
              <p>No project assignments yet</p>
              <Button className="mt-4" onClick={() => setAssignDialog(true)}>
                Assign to Project
              </Button>
            </div>
          ) : (
            <div className="space-y-4">
              {assignments.map((assignment) => (
                <Card key={assignment.assignment_id} className="border-l-4 border-l-primary">
                  <CardContent className="pt-4">
                    <div className="flex items-start justify-between mb-3">
                      <div>
                        <h3 className="font-semibold">{assignment.project_name}</h3>
                        <p className="text-sm text-muted-foreground">
                          {assignment.start_date} to {assignment.end_date}
                        </p>
                      </div>
                      <div className="text-right">
                        <p className="text-sm text-muted-foreground">Day Rate</p>
                        <p className="font-bold">E£{assignment.day_rate?.toLocaleString()}</p>
                      </div>
                    </div>
                    
                    <div className="grid grid-cols-3 gap-4 p-3 bg-muted/30 rounded-lg">
                      <div>
                        <p className="text-xs text-muted-foreground">Days Worked</p>
                        <p className="font-semibold">{assignment.days_worked || 0}</p>
                      </div>
                      <div>
                        <p className="text-xs text-muted-foreground">Total Cost</p>
                        <p className="font-semibold text-green-600">E£{assignment.total_cost?.toLocaleString() || 0}</p>
                      </div>
                      <div className="flex justify-end">
                        <Button
                          size="sm"
                          onClick={() => {
                            setSelectedAssignment(assignment);
                            loadAttendance(assignment.assignment_id);
                            setAttendanceDialog(true);
                          }}
                        >
                          <Clock className="w-4 h-4 mr-1" />
                          Record Attendance
                        </Button>
                      </div>
                    </div>

                    {/* Attendance Records for this assignment */}
                    {selectedAssignment?.assignment_id === assignment.assignment_id && attendance.length > 0 && (
                      <div className="mt-4 border-t pt-4">
                        <p className="text-sm font-medium mb-2">Recent Attendance:</p>
                        <div className="space-y-2">
                          {attendance.slice(0, 5).map((record) => (
                            <div key={record.attendance_id} className="flex items-center justify-between text-sm p-2 bg-background rounded">
                              <span>{record.work_date}</span>
                              <span className="text-muted-foreground">
                                {record.time_in} - {record.time_out} ({record.hours_worked}h)
                              </span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Assign to Project Dialog */}
      <Dialog open={assignDialog} onOpenChange={setAssignDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Assign to Project</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleAssignProject} className="space-y-4">
            <div className="space-y-2">
              <Label>Project *</Label>
              <Select value={assignForm.project_id} onValueChange={(value) => setAssignForm({ ...assignForm, project_id: value })}>
                <SelectTrigger>
                  <SelectValue placeholder="Select project" />
                </SelectTrigger>
                <SelectContent>
                  {projects.map((project) => (
                    <SelectItem key={project.project_id} value={project.project_id}>
                      {project.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            
            <div className="space-y-2">
              <Label>Day Rate (E£) *</Label>
              <Input
                type="number"
                step="0.01"
                min="0"
                value={assignForm.day_rate}
                onChange={(e) => setAssignForm({ ...assignForm, day_rate: e.target.value })}
                placeholder="500"
                required
              />
            </div>
            
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Start Date *</Label>
                <Input
                  type="date"
                  value={assignForm.start_date}
                  onChange={(e) => setAssignForm({ ...assignForm, start_date: e.target.value })}
                  required
                />
              </div>
              <div className="space-y-2">
                <Label>End Date *</Label>
                <Input
                  type="date"
                  value={assignForm.end_date}
                  onChange={(e) => setAssignForm({ ...assignForm, end_date: e.target.value })}
                  required
                />
              </div>
            </div>

            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setAssignDialog(false)}>
                Cancel
              </Button>
              <Button type="submit" disabled={saving}>
                {saving ? <LoadingSpinner size="sm" className="mr-2" /> : null}
                Assign to Project
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Record Attendance Dialog */}
      <Dialog open={attendanceDialog} onOpenChange={setAttendanceDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Record Attendance</DialogTitle>
            {selectedAssignment && (
              <p className="text-sm text-muted-foreground">
                {employee.full_name} - {selectedAssignment.project_name}
              </p>
            )}
          </DialogHeader>
          <form onSubmit={handleRecordAttendance} className="space-y-4">
            <div className="space-y-2">
              <Label>Work Date *</Label>
              <Input
                type="date"
                value={attendanceForm.work_date}
                onChange={(e) => setAttendanceForm({ ...attendanceForm, work_date: e.target.value })}
                required
              />
            </div>
            
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Time In *</Label>
                <Input
                  type="time"
                  value={attendanceForm.time_in}
                  onChange={(e) => setAttendanceForm({ ...attendanceForm, time_in: e.target.value })}
                  required
                />
              </div>
              <div className="space-y-2">
                <Label>Time Out *</Label>
                <Input
                  type="time"
                  value={attendanceForm.time_out}
                  onChange={(e) => setAttendanceForm({ ...attendanceForm, time_out: e.target.value })}
                  required
                />
              </div>
            </div>

            {selectedAssignment && attendance.length > 0 && (
              <div className="p-3 bg-muted rounded-lg">
                <p className="text-sm font-medium mb-2">Recent Attendance ({attendance.length} days):</p>
                <div className="space-y-1 max-h-[150px] overflow-y-auto">
                  {attendance.map((record) => (
                    <div key={record.attendance_id} className="flex justify-between text-xs p-1">
                      <span>{record.work_date}</span>
                      <span className="text-muted-foreground">{record.time_in} - {record.time_out}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setAttendanceDialog(false)}>
                Cancel
              </Button>
              <Button type="submit" disabled={saving}>
                {saving ? <LoadingSpinner size="sm" className="mr-2" /> : <CheckCircle className="w-4 h-4 mr-2" />}
                Record Attendance
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
}
