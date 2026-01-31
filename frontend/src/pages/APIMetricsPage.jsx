import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Badge } from "../components/ui/badge";
import { LoadingSpinner } from "../components/ui/loading-spinner";
import { Activity, TrendingUp, AlertCircle, Clock, Zap } from "lucide-react";
import { toast } from "sonner";

export default function APIMetricsPage() {
  const [summary, setSummary] = useState(null);
  const [endpoints, setEndpoints] = useState([]);
  const [errors, setErrors] = useState([]);
  const [loading, setLoading] = useState(true);
  const [hours, setHours] = useState(24);

  useEffect(() => {
    loadMetrics();
    // Auto-refresh every 30 seconds
    const interval = setInterval(loadMetrics, 30000);
    return () => clearInterval(interval);
  }, [hours]);

  const loadMetrics = async () => {
    try {
      const API_URL = process.env.REACT_APP_BACKEND_URL;
      const token = localStorage.getItem('proflow_token');
      
      const [summaryRes, endpointsRes, errorsRes] = await Promise.all([
        fetch(`${API_URL}/api/metrics/summary?hours=${hours}`, {
          headers: { 'Authorization': `Bearer ${token}` }
        }),
        fetch(`${API_URL}/api/metrics/endpoints?hours=${hours}&limit=10`, {
          headers: { 'Authorization': `Bearer ${token}` }
        }),
        fetch(`${API_URL}/api/metrics/errors?hours=${hours}&limit=20`, {
          headers: { 'Authorization': `Bearer ${token}` }
        })
      ]);
      
      const summaryData = await summaryRes.json();
      const endpointsData = await endpointsRes.json();
      const errorsData = await errorsRes.json();
      
      setSummary(summaryData);
      setEndpoints(endpointsData.endpoints || []);
      setErrors(errorsData.errors || []);
    } catch (error) {
      console.error('Failed to load metrics:', error);
      toast.error('Failed to load API metrics');
    } finally {
      setLoading(false);
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
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Activity className="w-8 h-8 text-blue-600" />
          <div>
            <h1 className="font-heading text-2xl sm:text-3xl font-bold tracking-tight">
              API Metrics Dashboard
            </h1>
            <p className="text-muted-foreground mt-1">
              Real-time API performance monitoring
            </p>
          </div>
        </div>
        <div className="flex gap-2">
          {[24, 48, 168].map(h => (
            <Badge
              key={h}
              variant={hours === h ? "default" : "outline"}
              className="cursor-pointer"
              onClick={() => setHours(h)}
            >
              {h}h
            </Badge>
          ))}
        </div>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Total Requests</p>
                <p className="text-2xl font-bold">{summary?.total_requests?.toLocaleString() || 0}</p>
              </div>
              <Zap className="w-8 h-8 text-blue-500" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Avg Response Time</p>
                <p className="text-2xl font-bold">{summary?.avg_response_time?.toFixed(0) || 0}ms</p>
              </div>
              <Clock className="w-8 h-8 text-green-500" />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Error Rate</p>
                <p className="text-2xl font-bold">{summary?.error_rate?.toFixed(1) || 0}%</p>
              </div>
              <AlertCircle className={`w-8 h-8 ${summary?.error_rate > 5 ? 'text-red-500' : 'text-yellow-500'}`} />
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Slow Requests</p>
                <p className="text-2xl font-bold">{summary?.slow_requests || 0}</p>
                <p className="text-xs text-muted-foreground">&gt;1000ms</p>
              </div>
              <TrendingUp className="w-8 h-8 text-orange-500" />
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid lg:grid-cols-2 gap-6">
        {/* Top Endpoints */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Top Endpoints</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {endpoints.map((endpoint, idx) => (
                <div key={idx} className="flex items-center justify-between p-2 border-b">
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-mono truncate">{endpoint.endpoint}</p>
                    <p className="text-xs text-muted-foreground">
                      {endpoint.request_count} requests • {endpoint.avg_response_time.toFixed(0)}ms avg
                    </p>
                  </div>
                  {endpoint.error_rate > 5 && (
                    <Badge variant="destructive" className="ml-2">
                      {endpoint.error_rate.toFixed(1)}% errors
                    </Badge>
                  )}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Recent Errors */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Recent Errors</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3 max-h-[400px] overflow-y-auto">
              {errors.length === 0 ? (
                <p className="text-sm text-muted-foreground text-center py-4">No errors in the last {hours} hours</p>
              ) : (
                errors.map((error, idx) => (
                  <div key={idx} className="p-3 bg-red-50 dark:bg-red-900/10 border border-red-200 dark:border-red-800 rounded-lg">
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <p className="text-sm font-mono text-red-700 dark:text-red-400">
                          {error.method} {error.endpoint}
                        </p>
                        <p className="text-xs text-muted-foreground mt-1">
                          Status {error.status_code} • {error.response_time_ms.toFixed(0)}ms
                        </p>
                        {error.error_message && (
                          <p className="text-xs mt-1 text-red-600">{error.error_message}</p>
                        )}
                      </div>
                      <Badge variant="destructive">{error.status_code}</Badge>
                    </div>
                  </div>
                ))
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
