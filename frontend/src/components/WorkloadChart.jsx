import { useState, useEffect, useMemo } from "react";
import { getWorkloadReport } from "../api/reports";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Badge } from "../components/ui/badge";
import { LoadingSpinner } from "../components/ui/loading-spinner";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
} from "recharts";
import { format, subDays } from "date-fns";
import { Users } from "lucide-react";

const COLORS = ['#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#EC4899', '#06B6D4', '#84CC16'];

export const WorkloadChart = ({ orgId }) => {
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (orgId) {
      loadData();
    }
  }, [orgId]);

  const loadData = async () => {
    setLoading(true);
    try {
      const startDate = format(subDays(new Date(), 30), "yyyy-MM-dd");
      const endDate = format(new Date(), "yyyy-MM-dd");
      const result = await getWorkloadReport(orgId, startDate, endDate);
      setData(result);
    } catch (err) {
      console.error("Failed to load workload data:", err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <Card>
        <CardContent className="flex items-center justify-center h-[300px]">
          <LoadingSpinner size="lg" />
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card>
        <CardContent className="flex items-center justify-center h-[300px] text-muted-foreground">
          Failed to load workload data
        </CardContent>
      </Card>
    );
  }

  if (!data || data.chart_data.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Users className="w-5 h-5" />
            Team Workload
          </CardTitle>
        </CardHeader>
        <CardContent className="flex items-center justify-center h-[250px] text-muted-foreground">
          No time entries in the last 30 days
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      {/* Bar Chart - Hours by Day */}
      <Card data-testid="workload-bar-chart">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Users className="w-5 h-5" />
            Team Workload (Last 30 Days)
          </CardTitle>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={data.chart_data}>
              <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
              <XAxis 
                dataKey="date" 
                tick={{ fontSize: 12 }}
                tickFormatter={(val) => format(new Date(val), "MMM d")}
              />
              <YAxis tick={{ fontSize: 12 }} />
              <Tooltip 
                contentStyle={{ 
                  backgroundColor: 'hsl(var(--card))', 
                  border: '1px solid hsl(var(--border))',
                  borderRadius: '6px'
                }}
                labelFormatter={(val) => format(new Date(val), "MMMM d, yyyy")}
              />
              <Legend />
              {data.users.map((user, index) => (
                <Bar 
                  key={user} 
                  dataKey={user} 
                  fill={COLORS[index % COLORS.length]}
                  radius={[4, 4, 0, 0]}
                />
              ))}
            </BarChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      {/* User Totals */}
      <div className="grid md:grid-cols-2 gap-6">
        {/* Pie Chart */}
        <Card data-testid="workload-pie-chart">
          <CardHeader>
            <CardTitle>Hours Distribution</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={250}>
              <PieChart>
                <Pie
                  data={data.user_totals}
                  dataKey="total_hours"
                  nameKey="name"
                  cx="50%"
                  cy="50%"
                  outerRadius={80}
                  label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
                >
                  {data.user_totals.map((_, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* User Summary Table */}
        <Card data-testid="workload-summary">
          <CardHeader>
            <CardTitle>Hours by Team Member</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {data.user_totals.map((user, index) => (
                <div key={user.user_id} className="flex items-center justify-between p-2 rounded-md hover:bg-accent">
                  <div className="flex items-center gap-3">
                    <div 
                      className="w-3 h-3 rounded-full" 
                      style={{ backgroundColor: COLORS[index % COLORS.length] }}
                    />
                    <span className="font-medium">{user.name}</span>
                  </div>
                  <Badge variant="secondary">{user.total_hours}h</Badge>
                </div>
              ))}
              <div className="border-t pt-3 flex items-center justify-between font-semibold">
                <span>Total</span>
                <Badge>{data.user_totals.reduce((sum, u) => sum + u.total_hours, 0).toFixed(1)}h</Badge>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default WorkloadChart;
