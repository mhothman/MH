import { useState, useEffect, useCallback } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../components/ui/card";
import { Button } from "../components/ui/button";
import { Badge } from "../components/ui/badge";
import { Progress } from "../components/ui/progress";
import { ScrollArea } from "../components/ui/scroll-area";
import { Switch } from "../components/ui/switch";
import { Label } from "../components/ui/label";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../components/ui/table";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "../components/ui/tooltip";
import { toast } from "sonner";
import {
  Activity,
  Database,
  HardDrive,
  Zap,
  AlertTriangle,
  CheckCircle2,
  RefreshCw,
  Play,
  Trash2,
  Clock,
  TrendingUp,
  Server,
  Layers,
  Timer,
  AlertCircle,
} from "lucide-react";
import {
  getDatabaseHealth,
  getQueryStats,
  resetQueryStats,
  getIndexInfo,
  createRecommendedIndexes,
  getCollectionStats,
  getSlowQueries,
} from "../api/health";

export default function PerformanceDashboard() {
  const [loading, setLoading] = useState(true);
  const [autoRefresh, setAutoRefresh] = useState(false);
  
  // Data states
  const [dbHealth, setDbHealth] = useState(null);
  const [queryStats, setQueryStats] = useState(null);
  const [indexInfo, setIndexInfo] = useState(null);
  const [collectionStats, setCollectionStats] = useState(null);
  const [slowQueries, setSlowQueries] = useState(null);
  
  // Action states
  const [creatingIndexes, setCreatingIndexes] = useState(false);
  const [resettingStats, setResettingStats] = useState(false);

  const loadAllData = useCallback(async () => {
    try {
      const [health, stats, indexes, collections, slow] = await Promise.all([
        getDatabaseHealth().catch(() => null),
        getQueryStats().catch(() => null),
        getIndexInfo().catch(() => null),
        getCollectionStats().catch(() => null),
        getSlowQueries().catch(() => null),
      ]);
      
      setDbHealth(health);
      setQueryStats(stats);
      setIndexInfo(indexes);
      setCollectionStats(collections);
      setSlowQueries(slow);
    } catch (error) {
      console.error("Failed to load performance data:", error);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadAllData();
  }, [loadAllData]);

  // Auto-refresh effect
  useEffect(() => {
    let interval = null;
    if (autoRefresh) {
      interval = setInterval(loadAllData, 5000); // Refresh every 5 seconds
    }
    return () => {
      if (interval) {
        clearInterval(interval);
      }
    };
  }, [autoRefresh, loadAllData]);

  const handleCreateIndexes = async () => {
    setCreatingIndexes(true);
    try {
      const result = await createRecommendedIndexes();
      toast.success(`Created ${result.result.created.length} indexes successfully`);
      loadAllData();
    } catch (error) {
      toast.error("Failed to create indexes: " + error.message);
    } finally {
      setCreatingIndexes(false);
    }
  };

  const handleResetStats = async () => {
    setResettingStats(true);
    try {
      await resetQueryStats();
      toast.success("Query statistics reset");
      loadAllData();
    } catch (error) {
      toast.error("Failed to reset stats: " + error.message);
    } finally {
      setResettingStats(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  const dbStatus = dbHealth?.status === "healthy";
  const totalDocuments = collectionStats?.collections 
    ? Object.values(collectionStats.collections).reduce((sum, c) => sum + (c.count || 0), 0)
    : 0;
  const missingIndexes = indexInfo?.indexes?.recommendations?.length || 0;

  return (
    <div className="space-y-6">
      {/* Header with controls */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Performance Dashboard</h2>
          <p className="text-muted-foreground">
            Monitor database health, query performance, and system metrics
          </p>
        </div>
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <Switch
              id="auto-refresh"
              checked={autoRefresh}
              onCheckedChange={setAutoRefresh}
            />
            <Label htmlFor="auto-refresh" className="text-sm">
              Auto-refresh (5s)
            </Label>
          </div>
          <Button variant="outline" size="sm" onClick={loadAllData}>
            <RefreshCw className="h-4 w-4 mr-2" />
            Refresh
          </Button>
        </div>
      </div>

      {/* Status Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Database Status */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Database Status</CardTitle>
            <Database className={`h-4 w-4 ${dbStatus ? 'text-green-500' : 'text-red-500'}`} />
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-2">
              {dbStatus ? (
                <CheckCircle2 className="h-5 w-5 text-green-500" />
              ) : (
                <AlertCircle className="h-5 w-5 text-red-500" />
              )}
              <span className="text-2xl font-bold">
                {dbStatus ? "Healthy" : "Unhealthy"}
              </span>
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              MongoDB {dbHealth?.connection?.server_version || "N/A"}
            </p>
          </CardContent>
        </Card>

        {/* Total Documents */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Documents</CardTitle>
            <Layers className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{totalDocuments.toLocaleString()}</div>
            <p className="text-xs text-muted-foreground mt-1">
              Across {Object.keys(collectionStats?.collections || {}).length} collections
            </p>
          </CardContent>
        </Card>

        {/* Storage */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Storage Used</CardTitle>
            <HardDrive className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {dbHealth?.database?.storage_size_mb?.toFixed(2) || "0"} MB
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              Data: {dbHealth?.database?.data_size_mb?.toFixed(2) || "0"} MB
            </p>
          </CardContent>
        </Card>

        {/* Index Health */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Index Health</CardTitle>
            <Zap className={`h-4 w-4 ${missingIndexes === 0 ? 'text-green-500' : 'text-yellow-500'}`} />
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-2">
              {missingIndexes === 0 ? (
                <CheckCircle2 className="h-5 w-5 text-green-500" />
              ) : (
                <AlertTriangle className="h-5 w-5 text-yellow-500" />
              )}
              <span className="text-2xl font-bold">
                {missingIndexes === 0 ? "Optimal" : `${missingIndexes} Missing`}
              </span>
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              {dbHealth?.database?.indexes || 0} indexes active
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Query Statistics & Slow Queries */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Query Statistics */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="flex items-center gap-2">
                  <Activity className="h-5 w-5" />
                  Query Statistics
                </CardTitle>
                <CardDescription>Real-time query performance metrics</CardDescription>
              </div>
              <Button 
                variant="outline" 
                size="sm" 
                onClick={handleResetStats}
                disabled={resettingStats}
              >
                {resettingStats ? (
                  <RefreshCw className="h-4 w-4 animate-spin" />
                ) : (
                  <Trash2 className="h-4 w-4" />
                )}
                <span className="ml-2">Reset</span>
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="grid grid-cols-3 gap-4">
                <div className="text-center p-3 bg-muted rounded-lg">
                  <div className="text-2xl font-bold">
                    {queryStats?.stats?.summary?.total_queries?.toLocaleString() || 0}
                  </div>
                  <div className="text-xs text-muted-foreground">Total Queries</div>
                </div>
                <div className="text-center p-3 bg-muted rounded-lg">
                  <div className="text-2xl font-bold text-yellow-600">
                    {queryStats?.stats?.summary?.slow_queries || 0}
                  </div>
                  <div className="text-xs text-muted-foreground">Slow Queries</div>
                </div>
                <div className="text-center p-3 bg-muted rounded-lg">
                  <div className="text-2xl font-bold">
                    {queryStats?.stats?.summary?.slow_query_percentage?.toFixed(1) || 0}%
                  </div>
                  <div className="text-xs text-muted-foreground">Slow %</div>
                </div>
              </div>

              {queryStats?.stats?.slowest_operations?.length > 0 && (
                <div>
                  <h4 className="text-sm font-medium mb-2">Slowest Operations</h4>
                  <ScrollArea className="h-[180px]">
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Operation</TableHead>
                          <TableHead className="text-right">Avg (ms)</TableHead>
                          <TableHead className="text-right">Max (ms)</TableHead>
                          <TableHead className="text-right">Count</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {queryStats.stats.slowest_operations.map((op, idx) => (
                          <TableRow key={idx}>
                            <TableCell className="font-mono text-xs">{op.operation}</TableCell>
                            <TableCell className="text-right">
                              <Badge variant={op.avg_ms > 100 ? "destructive" : "secondary"}>
                                {op.avg_ms.toFixed(1)}
                              </Badge>
                            </TableCell>
                            <TableCell className="text-right">
                              <Badge variant={op.max_ms > 500 ? "destructive" : "outline"}>
                                {op.max_ms.toFixed(1)}
                              </Badge>
                            </TableCell>
                            <TableCell className="text-right">{op.count}</TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </ScrollArea>
                </div>
              )}

              {(!queryStats?.stats?.slowest_operations || queryStats.stats.slowest_operations.length === 0) && (
                <div className="text-center py-8 text-muted-foreground">
                  <Timer className="h-8 w-8 mx-auto mb-2 opacity-50" />
                  <p>No query data yet. Statistics will appear as queries are executed.</p>
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Slow Queries Alert */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <AlertTriangle className="h-5 w-5 text-yellow-500" />
              Slow Query Alerts
            </CardTitle>
            <CardDescription>
              Queries exceeding {slowQueries?.thresholds?.slow_ms || 100}ms threshold
            </CardDescription>
          </CardHeader>
          <CardContent>
            {slowQueries?.queries?.length > 0 ? (
              <ScrollArea className="h-[280px]">
                <div className="space-y-3">
                  {slowQueries.queries.map((query, idx) => (
                    <div 
                      key={idx} 
                      className={`p-3 rounded-lg border ${
                        query.duration_ms >= (slowQueries?.thresholds?.very_slow_ms || 500)
                          ? 'border-red-200 bg-red-50 dark:border-red-900 dark:bg-red-950'
                          : 'border-yellow-200 bg-yellow-50 dark:border-yellow-900 dark:bg-yellow-950'
                      }`}
                    >
                      <div className="flex items-center justify-between mb-1">
                        <span className="font-mono text-sm font-medium">
                          {query.collection}.{query.operation}
                        </span>
                        <Badge 
                          variant={query.duration_ms >= (slowQueries?.thresholds?.very_slow_ms || 500) ? "destructive" : "warning"}
                        >
                          {query.duration_ms.toFixed(1)}ms
                        </Badge>
                      </div>
                      <div className="flex items-center gap-2 text-xs text-muted-foreground">
                        <Clock className="h-3 w-3" />
                        {new Date(query.timestamp).toLocaleString()}
                      </div>
                      {query.filter && (
                        <div className="mt-1 text-xs font-mono text-muted-foreground truncate">
                          Filter: {query.filter}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </ScrollArea>
            ) : (
              <div className="text-center py-12 text-muted-foreground">
                <CheckCircle2 className="h-12 w-12 mx-auto mb-3 text-green-500 opacity-50" />
                <p className="font-medium">No Slow Queries Detected</p>
                <p className="text-sm">All queries are performing within acceptable thresholds</p>
              </div>
            )}

            {slowQueries?.summary && (
              <div className="mt-4 pt-4 border-t flex justify-between text-sm">
                <span className="text-muted-foreground">
                  Total slow queries: {slowQueries.summary.total_slow_queries}
                </span>
                <span className="text-red-600">
                  Very slow: {slowQueries.summary.very_slow_queries}
                </span>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Collection Stats & Index Recommendations */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Collection Statistics */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Server className="h-5 w-5" />
              Collection Statistics
            </CardTitle>
            <CardDescription>Document counts per collection</CardDescription>
          </CardHeader>
          <CardContent>
            <ScrollArea className="h-[300px]">
              <div className="space-y-3">
                {collectionStats?.collections && Object.entries(collectionStats.collections)
                  .sort((a, b) => (b[1].count || 0) - (a[1].count || 0))
                  .map(([name, stats]) => {
                    const count = stats.count || 0;
                    const maxCount = Math.max(...Object.values(collectionStats.collections).map(c => c.count || 0));
                    const percentage = maxCount > 0 ? (count / maxCount) * 100 : 0;
                    
                    return (
                      <div key={name} className="space-y-1">
                        <div className="flex items-center justify-between text-sm">
                          <span className="font-medium">{name}</span>
                          <span className="text-muted-foreground">{count.toLocaleString()}</span>
                        </div>
                        <Progress value={percentage} className="h-2" />
                      </div>
                    );
                  })}
              </div>
            </ScrollArea>
          </CardContent>
        </Card>

        {/* Index Recommendations */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="flex items-center gap-2">
                  <TrendingUp className="h-5 w-5" />
                  Index Recommendations
                </CardTitle>
                <CardDescription>Optimize query performance with indexes</CardDescription>
              </div>
              {missingIndexes > 0 && (
                <Button 
                  onClick={handleCreateIndexes} 
                  disabled={creatingIndexes}
                  size="sm"
                >
                  {creatingIndexes ? (
                    <RefreshCw className="h-4 w-4 animate-spin mr-2" />
                  ) : (
                    <Play className="h-4 w-4 mr-2" />
                  )}
                  Create All
                </Button>
              )}
            </div>
          </CardHeader>
          <CardContent>
            {indexInfo?.indexes?.recommendations?.length > 0 ? (
              <ScrollArea className="h-[300px]">
                <div className="space-y-3">
                  {indexInfo.indexes.recommendations.map((rec, idx) => (
                    <div key={idx} className="p-3 rounded-lg border bg-muted/50">
                      <div className="flex items-center gap-2 mb-2">
                        <Badge variant="outline">{rec.collection}</Badge>
                        <span className="font-mono text-sm">{rec.index}</span>
                      </div>
                      <div className="text-xs text-muted-foreground">
                        Keys: {rec.keys.map(k => `${k[0]} (${k[1] === 1 ? 'asc' : 'desc'})`).join(', ')}
                      </div>
                      <div className="text-xs text-muted-foreground mt-1">
                        {rec.reason}
                      </div>
                    </div>
                  ))}
                </div>
              </ScrollArea>
            ) : (
              <div className="text-center py-12 text-muted-foreground">
                <CheckCircle2 className="h-12 w-12 mx-auto mb-3 text-green-500 opacity-50" />
                <p className="font-medium">All Recommended Indexes Created</p>
                <p className="text-sm">Database is optimized for query performance</p>
              </div>
            )}

            {indexInfo?.indexes?.existing_indexes && (
              <div className="mt-4 pt-4 border-t">
                <h4 className="text-sm font-medium mb-2">Existing Indexes</h4>
                <div className="flex flex-wrap gap-2">
                  {Object.entries(indexInfo.indexes.existing_indexes).map(([collection, indexes]) => (
                    <TooltipProvider key={collection}>
                      <Tooltip>
                        <TooltipTrigger>
                          <Badge variant="secondary" className="cursor-help">
                            {collection}: {indexes.length}
                          </Badge>
                        </TooltipTrigger>
                        <TooltipContent>
                          <div className="text-xs">
                            {indexes.join(', ')}
                          </div>
                        </TooltipContent>
                      </Tooltip>
                    </TooltipProvider>
                  ))}
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Last Updated */}
      <div className="text-center text-sm text-muted-foreground">
        Last updated: {new Date().toLocaleString()}
        {autoRefresh && <span className="ml-2">(Auto-refreshing every 5s)</span>}
      </div>
    </div>
  );
}
