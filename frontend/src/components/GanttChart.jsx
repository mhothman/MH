import { useState, useEffect, useMemo, useRef, useCallback } from "react";
import { getTimelineData } from "../api/reports";
import { updateTask } from "../api/tasks";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import { Badge } from "./ui/badge";
import { Button } from "./ui/button";
import { Switch } from "./ui/switch";
import { Label } from "./ui/label";
import { LoadingSpinner } from "./ui/loading-spinner";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "./ui/tooltip";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "./ui/dropdown-menu";
import { toast } from "sonner";
import html2canvas from "html2canvas";
import { jsPDF } from "jspdf";
import { 
  format, 
  differenceInDays, 
  parseISO, 
  addDays, 
  startOfDay, 
  isValid,
  isSameDay,
  isWeekend 
} from "date-fns";
import { 
  CalendarDays, 
  AlertCircle, 
  ArrowRight, 
  Zap, 
  GitBranch,
  Layers,
  RefreshCw,
  ChevronLeft,
  ChevronRight,
  ZoomIn,
  ZoomOut,
  Download,
  FileImage,
  FileText,
  Share2
} from "lucide-react";

const STATUS_COLORS = {
  todo: { bg: "bg-slate-400", hex: "#94a3b8" },
  in_progress: { bg: "bg-blue-500", hex: "#3b82f6" },
  review: { bg: "bg-purple-500", hex: "#a855f7" },
  done: { bg: "bg-green-500", hex: "#22c55e" },
};

const PRIORITY_COLORS = {
  urgent: { border: "border-red-500", hex: "#ef4444" },
  high: { border: "border-orange-500", hex: "#f97316" },
  medium: { border: "border-yellow-500", hex: "#eab308" },
  low: { border: "border-green-500", hex: "#22c55e" },
};

// Calculate critical path using longest path algorithm
const calculateCriticalPath = (tasks) => {
  const taskMap = new Map(tasks.map(t => [t.task_id, t]));
  const criticalTasks = new Set();
  
  // Build dependency graph
  const inDegree = new Map();
  const outEdges = new Map();
  
  tasks.forEach(task => {
    inDegree.set(task.task_id, (task.blocked_by || []).length);
    outEdges.set(task.task_id, []);
  });
  
  tasks.forEach(task => {
    (task.blocked_by || []).forEach(blockerId => {
      if (outEdges.has(blockerId)) {
        outEdges.get(blockerId).push(task.task_id);
      }
    });
  });
  
  // Find longest path using dynamic programming
  const longestPath = new Map();
  const predecessor = new Map();
  
  // Topological sort + longest path calculation
  const queue = tasks.filter(t => (t.blocked_by || []).length === 0).map(t => t.task_id);
  
  tasks.forEach(t => {
    longestPath.set(t.task_id, t.duration || 1);
    predecessor.set(t.task_id, null);
  });
  
  while (queue.length > 0) {
    const taskId = queue.shift();
    const task = taskMap.get(taskId);
    const currentPath = longestPath.get(taskId);
    
    (outEdges.get(taskId) || []).forEach(dependentId => {
      const dependent = taskMap.get(dependentId);
      const newPath = currentPath + (dependent?.duration || 1);
      
      if (newPath > longestPath.get(dependentId)) {
        longestPath.set(dependentId, newPath);
        predecessor.set(dependentId, taskId);
      }
      
      const newInDegree = inDegree.get(dependentId) - 1;
      inDegree.set(dependentId, newInDegree);
      
      if (newInDegree === 0) {
        queue.push(dependentId);
      }
    });
  }
  
  // Find the task with the longest path (end of critical path)
  let maxPath = 0;
  let endTask = null;
  
  longestPath.forEach((path, taskId) => {
    if (path > maxPath) {
      maxPath = path;
      endTask = taskId;
    }
  });
  
  // Backtrack to find all critical path tasks
  let current = endTask;
  while (current) {
    criticalTasks.add(current);
    current = predecessor.get(current);
  }
  
  return criticalTasks;
};

export const GanttChart = ({ projectId, onTaskClick }) => {
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [showDependencies, setShowDependencies] = useState(true);
  const [showCriticalPath, setShowCriticalPath] = useState(true);
  const [showBaseline, setShowBaseline] = useState(false);
  const [zoom, setZoom] = useState(1);
  const [draggedTask, setDraggedTask] = useState(null);
  const [dragOffset, setDragOffset] = useState({ x: 0, startOffset: 0 });
  const [exporting, setExporting] = useState(false);
  const containerRef = useRef(null);
  const svgRef = useRef(null);
  const chartRef = useRef(null);

  useEffect(() => {
    if (projectId) {
      loadData();
    }
  }, [projectId]);

  const loadData = async () => {
    setLoading(true);
    try {
      const result = await getTimelineData(projectId);
      setData(result);
    } catch (err) {
      console.error("Failed to load timeline data:", err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // Export to PNG
  const exportToPNG = async () => {
    if (!chartRef.current) return;
    
    setExporting(true);
    toast.info("Generating PNG...");
    
    try {
      const canvas = await html2canvas(chartRef.current, {
        backgroundColor: '#ffffff',
        scale: 2,
        logging: false,
        useCORS: true,
        allowTaint: true,
      });
      
      const link = document.createElement('a');
      link.download = `gantt-chart-${data?.project?.name || 'project'}-${format(new Date(), 'yyyy-MM-dd')}.png`;
      link.href = canvas.toDataURL('image/png');
      link.click();
      
      toast.success("PNG exported successfully!");
    } catch (err) {
      console.error("Failed to export PNG:", err);
      toast.error("Failed to export PNG");
    } finally {
      setExporting(false);
    }
  };

  // Export to PDF
  const exportToPDF = async () => {
    if (!chartRef.current) return;
    
    setExporting(true);
    toast.info("Generating PDF...");
    
    try {
      const canvas = await html2canvas(chartRef.current, {
        backgroundColor: '#ffffff',
        scale: 2,
        logging: false,
        useCORS: true,
        allowTaint: true,
      });
      
      const imgData = canvas.toDataURL('image/png');
      const imgWidth = canvas.width;
      const imgHeight = canvas.height;
      
      // Calculate PDF dimensions (landscape for wide charts)
      const pdfWidth = imgWidth > imgHeight ? 297 : 210; // A4 dimensions in mm
      const pdfHeight = imgWidth > imgHeight ? 210 : 297;
      
      const pdf = new jsPDF({
        orientation: imgWidth > imgHeight ? 'landscape' : 'portrait',
        unit: 'mm',
        format: 'a4'
      });
      
      // Add title
      pdf.setFontSize(16);
      pdf.text(`${data?.project?.name || 'Project'} - Gantt Chart`, 14, 15);
      pdf.setFontSize(10);
      pdf.setTextColor(128);
      pdf.text(`Generated on ${format(new Date(), 'MMMM d, yyyy')}`, 14, 22);
      
      // Calculate image dimensions to fit on page
      const margin = 14;
      const availableWidth = pdfWidth - (margin * 2);
      const availableHeight = pdfHeight - 35; // Account for title
      
      const ratio = Math.min(availableWidth / imgWidth, availableHeight / imgHeight);
      const scaledWidth = imgWidth * ratio;
      const scaledHeight = imgHeight * ratio;
      
      pdf.addImage(imgData, 'PNG', margin, 28, scaledWidth, scaledHeight);
      
      pdf.save(`gantt-chart-${data?.project?.name || 'project'}-${format(new Date(), 'yyyy-MM-dd')}.pdf`);
      
      toast.success("PDF exported successfully!");
    } catch (err) {
      console.error("Failed to export PDF:", err);
      toast.error("Failed to export PDF");
    } finally {
      setExporting(false);
    }
  };

  const { dateRange, dayWidth, tasks, minDate, criticalPath } = useMemo(() => {
    if (!data || !data.tasks.length) {
      return { dateRange: [], dayWidth: 40, tasks: [], minDate: new Date(), criticalPath: new Set() };
    }

    const baseDayWidth = 40 * zoom;
    let min = new Date();
    let max = new Date();

    data.tasks.forEach((task) => {
      if (task.start) {
        const start = parseISO(task.start);
        if (isValid(start) && start < min) min = start;
      }
      if (task.end) {
        const end = parseISO(task.end);
        if (isValid(end) && end > max) max = end;
      }
    });

    min = addDays(startOfDay(min), -3);
    max = addDays(startOfDay(max), 7);

    const totalDays = differenceInDays(max, min) + 1;
    const dateRange = [];
    for (let i = 0; i < totalDays; i++) {
      dateRange.push(addDays(min, i));
    }

    const processedTasks = data.tasks.map((task) => {
      const start = task.start ? parseISO(task.start) : min;
      const end = task.end ? parseISO(task.end) : addDays(start, 3);
      const duration = differenceInDays(end, start) + 1;
      
      // Baseline dates (original planned dates - simulated as 2 days earlier for demo)
      const baselineStart = task.baseline_start ? parseISO(task.baseline_start) : addDays(start, -2);
      const baselineEnd = task.baseline_end ? parseISO(task.baseline_end) : addDays(end, -1);
      
      return {
        ...task,
        startOffset: differenceInDays(start, min),
        duration,
        startDate: start,
        endDate: end,
        baselineStartOffset: differenceInDays(baselineStart, min),
        baselineDuration: differenceInDays(baselineEnd, baselineStart) + 1,
      };
    });

    const criticalPath = calculateCriticalPath(processedTasks);

    return {
      dateRange,
      dayWidth: baseDayWidth,
      tasks: processedTasks,
      minDate: min,
      criticalPath,
    };
  }, [data, zoom]);

  // Handle drag start
  const handleDragStart = useCallback((e, task) => {
    e.preventDefault();
    const rect = e.currentTarget.getBoundingClientRect();
    setDraggedTask(task);
    setDragOffset({
      x: e.clientX - rect.left,
      startOffset: task.startOffset
    });
  }, []);

  // Handle drag move
  const handleDragMove = useCallback((e) => {
    if (!draggedTask || !containerRef.current) return;
    
    const containerRect = containerRef.current.getBoundingClientRect();
    const taskListWidth = 200; // Width of task name column
    const newX = e.clientX - containerRect.left - taskListWidth - dragOffset.x;
    const newStartOffset = Math.max(0, Math.round(newX / dayWidth));
    
    // Update task position visually
    setDraggedTask(prev => ({
      ...prev,
      startOffset: newStartOffset
    }));
  }, [draggedTask, dayWidth, dragOffset]);

  // Handle drag end
  const handleDragEnd = useCallback(async () => {
    if (!draggedTask) return;
    
    const originalTask = tasks.find(t => t.task_id === draggedTask.task_id);
    if (originalTask && originalTask.startOffset !== draggedTask.startOffset) {
      const daysDiff = draggedTask.startOffset - originalTask.startOffset;
      const newStartDate = addDays(originalTask.startDate, daysDiff);
      const newEndDate = addDays(originalTask.endDate, daysDiff);
      
      try {
        await updateTask(draggedTask.task_id, {
          start_date: newStartDate.toISOString(),
          due_date: newEndDate.toISOString()
        });
        toast.success("Task dates updated");
        loadData(); // Reload data
      } catch (error) {
        toast.error("Failed to update task dates");
      }
    }
    
    setDraggedTask(null);
    setDragOffset({ x: 0, startOffset: 0 });
  }, [draggedTask, tasks, dayWidth, minDate]);

  // Add/remove event listeners for drag
  useEffect(() => {
    if (draggedTask) {
      window.addEventListener('mousemove', handleDragMove);
      window.addEventListener('mouseup', handleDragEnd);
      return () => {
        window.removeEventListener('mousemove', handleDragMove);
        window.removeEventListener('mouseup', handleDragEnd);
      };
    }
  }, [draggedTask, handleDragMove, handleDragEnd]);

  // Render dependency arrows
  const renderDependencyArrows = () => {
    if (!showDependencies) return null;
    
    const arrows = [];
    const taskPositions = new Map();
    
    // Calculate task positions
    tasks.forEach((task, index) => {
      taskPositions.set(task.task_id, {
        x: task.startOffset * dayWidth + (task.duration * dayWidth) / 2,
        y: index * 50 + 25,
        endX: (task.startOffset + task.duration) * dayWidth,
        startX: task.startOffset * dayWidth,
      });
    });
    
    tasks.forEach((task) => {
      (task.blocked_by || []).forEach(blockerId => {
        const fromPos = taskPositions.get(blockerId);
        const toPos = taskPositions.get(task.task_id);
        
        if (fromPos && toPos) {
          const isCritical = showCriticalPath && criticalPath.has(task.task_id) && criticalPath.has(blockerId);
          const isComplete = tasks.find(t => t.task_id === blockerId)?.status === 'done';
          
          // Calculate control points for curved arrow
          const startX = fromPos.endX;
          const startY = fromPos.y;
          const endX = toPos.startX;
          const endY = toPos.y;
          const midX = (startX + endX) / 2;
          
          arrows.push(
            <g key={`${blockerId}-${task.task_id}`}>
              <path
                d={`M ${startX} ${startY} C ${midX} ${startY}, ${midX} ${endY}, ${endX} ${endY}`}
                fill="none"
                stroke={isCritical ? "#ef4444" : isComplete ? "#22c55e" : "#94a3b8"}
                strokeWidth={isCritical ? 2.5 : 1.5}
                strokeDasharray={isComplete ? "none" : "5,3"}
                markerEnd={`url(#arrow-${isCritical ? 'critical' : isComplete ? 'complete' : 'default'})`}
                className="transition-all"
              />
            </g>
          );
        }
      });
    });
    
    return (
      <svg 
        ref={svgRef}
        className="absolute top-0 left-[200px] pointer-events-none" 
        style={{ width: dateRange.length * dayWidth, height: tasks.length * 50 }}
      >
        <defs>
          <marker id="arrow-default" markerWidth="10" markerHeight="10" refX="9" refY="3" orient="auto">
            <path d="M0,0 L0,6 L9,3 z" fill="#94a3b8" />
          </marker>
          <marker id="arrow-critical" markerWidth="10" markerHeight="10" refX="9" refY="3" orient="auto">
            <path d="M0,0 L0,6 L9,3 z" fill="#ef4444" />
          </marker>
          <marker id="arrow-complete" markerWidth="10" markerHeight="10" refX="9" refY="3" orient="auto">
            <path d="M0,0 L0,6 L9,3 z" fill="#22c55e" />
          </marker>
        </defs>
        {arrows}
      </svg>
    );
  };

  if (loading) {
    return (
      <Card>
        <CardContent className="flex items-center justify-center h-[400px]">
          <LoadingSpinner size="lg" />
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card>
        <CardContent className="flex items-center justify-center h-[400px] text-muted-foreground">
          Failed to load timeline data
        </CardContent>
      </Card>
    );
  }

  if (!data || tasks.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <CalendarDays className="w-5 h-5" />
            Project Timeline
          </CardTitle>
        </CardHeader>
        <CardContent className="flex items-center justify-center h-[300px] text-muted-foreground">
          No tasks with dates to display
        </CardContent>
      </Card>
    );
  }

  return (
    <Card data-testid="gantt-chart-enhanced">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between flex-wrap gap-4">
          <CardTitle className="flex items-center gap-2">
            <CalendarDays className="w-5 h-5" />
            {data.project.name} - Timeline
          </CardTitle>
          
          {/* Controls */}
          <div className="flex items-center gap-4 flex-wrap">
            {/* Zoom Controls */}
            <div className="flex items-center gap-1">
              <Button 
                variant="outline" 
                size="icon" 
                className="h-8 w-8"
                onClick={() => setZoom(z => Math.max(0.5, z - 0.25))}
                disabled={zoom <= 0.5}
              >
                <ZoomOut className="w-4 h-4" />
              </Button>
              <span className="text-sm w-12 text-center">{Math.round(zoom * 100)}%</span>
              <Button 
                variant="outline" 
                size="icon" 
                className="h-8 w-8"
                onClick={() => setZoom(z => Math.min(2, z + 0.25))}
                disabled={zoom >= 2}
              >
                <ZoomIn className="w-4 h-4" />
              </Button>
            </div>
            
            {/* Toggle Options */}
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2">
                <Switch 
                  id="deps" 
                  checked={showDependencies} 
                  onCheckedChange={setShowDependencies}
                />
                <Label htmlFor="deps" className="text-sm cursor-pointer flex items-center gap-1">
                  <GitBranch className="w-3 h-3" />
                  Dependencies
                </Label>
              </div>
              
              <div className="flex items-center gap-2">
                <Switch 
                  id="critical" 
                  checked={showCriticalPath} 
                  onCheckedChange={setShowCriticalPath}
                />
                <Label htmlFor="critical" className="text-sm cursor-pointer flex items-center gap-1">
                  <Zap className="w-3 h-3" />
                  Critical Path
                </Label>
              </div>
              
              <div className="flex items-center gap-2">
                <Switch 
                  id="baseline" 
                  checked={showBaseline} 
                  onCheckedChange={setShowBaseline}
                />
                <Label htmlFor="baseline" className="text-sm cursor-pointer flex items-center gap-1">
                  <Layers className="w-3 h-3" />
                  Baseline
                </Label>
              </div>
            </div>
            
            <Button variant="outline" size="sm" onClick={loadData}>
              <RefreshCw className="w-4 h-4 mr-1" />
              Refresh
            </Button>
            
            {/* Export Dropdown */}
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="outline" size="sm" disabled={exporting}>
                  {exporting ? (
                    <LoadingSpinner size="sm" className="mr-1" />
                  ) : (
                    <Download className="w-4 h-4 mr-1" />
                  )}
                  Export
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuItem onClick={exportToPNG} data-testid="export-png-btn">
                  <FileImage className="w-4 h-4 mr-2" />
                  Export as PNG
                </DropdownMenuItem>
                <DropdownMenuItem onClick={exportToPDF} data-testid="export-pdf-btn">
                  <FileText className="w-4 h-4 mr-2" />
                  Export as PDF
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </div>
      </CardHeader>
      
      <CardContent>
        <div 
          ref={chartRef}
          className="bg-card"
        >
        <div 
          ref={containerRef}
          className="overflow-x-auto relative"
          style={{ cursor: draggedTask ? 'grabbing' : 'default' }}
        >
          <div style={{ minWidth: dateRange.length * dayWidth + 200 }}>
            {/* Header - Dates */}
            <div className="flex border-b border-border sticky top-0 bg-card z-20">
              <div className="w-[200px] flex-shrink-0 p-2 font-medium border-r border-border">
                Task
              </div>
              <div className="flex relative">
                {dateRange.map((date, i) => {
                  const isToday = isSameDay(date, new Date());
                  const weekend = isWeekend(date);
                  return (
                    <div
                      key={i}
                      className={`text-center text-xs border-r border-border/50 py-2 ${
                        isToday ? 'bg-primary/10 font-bold' : weekend ? 'bg-muted/30' : ''
                      }`}
                      style={{ width: dayWidth }}
                    >
                      <div className={isToday ? 'text-primary' : 'text-muted-foreground'}>
                        {format(date, "d")}
                      </div>
                      <div className="text-[10px] text-muted-foreground">{format(date, "EEE")}</div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Today Line */}
            {dateRange.some(d => isSameDay(d, new Date())) && (
              <div 
                className="absolute top-0 bottom-0 w-0.5 bg-primary z-10 pointer-events-none"
                style={{ 
                  left: 200 + dateRange.findIndex(d => isSameDay(d, new Date())) * dayWidth + dayWidth / 2 
                }}
              />
            )}

            {/* Tasks */}
            <div className="divide-y divide-border relative">
              {renderDependencyArrows()}
              
              {tasks.map((task, index) => {
                const displayTask = draggedTask?.task_id === task.task_id ? draggedTask : task;
                const isCritical = showCriticalPath && criticalPath.has(task.task_id);
                const isBlocked = (task.blocked_by || []).some(blockerId => {
                  const blocker = tasks.find(t => t.task_id === blockerId);
                  return blocker && blocker.status !== 'done';
                });
                
                return (
                  <div key={task.task_id} className="flex items-center min-h-[50px] relative">
                    {/* Task Name */}
                    <div className="w-[200px] flex-shrink-0 p-2 border-r border-border bg-card z-10">
                      <TooltipProvider>
                        <Tooltip>
                          <TooltipTrigger asChild>
                            <div 
                              className={`truncate text-sm font-medium cursor-pointer hover:text-primary transition-colors ${
                                isCritical ? 'text-red-500' : ''
                              }`}
                              onClick={() => onTaskClick && onTaskClick(task)}
                            >
                              {isCritical && <Zap className="w-3 h-3 inline mr-1 text-red-500" />}
                              {task.title}
                            </div>
                          </TooltipTrigger>
                          <TooltipContent side="right" className="max-w-xs">
                            <div className="space-y-2">
                              <p className="font-medium">{task.title}</p>
                              <div className="text-xs space-y-1">
                                <p>
                                  📅 {task.start && format(parseISO(task.start), "MMM d")} - 
                                  {task.end && format(parseISO(task.end), " MMM d, yyyy")}
                                </p>
                                <p>⏱️ Duration: {task.duration} days</p>
                                <p>📊 Progress: {task.progress}%</p>
                                {task.assignees?.length > 0 && (
                                  <p>👤 {task.assignees.join(", ")}</p>
                                )}
                                {isCritical && (
                                  <Badge variant="destructive" className="text-[10px]">
                                    Critical Path
                                  </Badge>
                                )}
                              </div>
                            </div>
                          </TooltipContent>
                        </Tooltip>
                      </TooltipProvider>
                      
                      <div className="flex items-center gap-1 mt-1">
                        {isBlocked && (
                          <Badge variant="outline" className="text-[10px] text-orange-500 border-orange-500">
                            <AlertCircle className="w-2 h-2 mr-0.5" />
                            Blocked
                          </Badge>
                        )}
                        {isCritical && (
                          <Badge variant="destructive" className="text-[10px]">
                            Critical
                          </Badge>
                        )}
                      </div>
                    </div>

                    {/* Timeline Bar Area */}
                    <div 
                      className="flex-1 relative h-[50px]"
                      style={{ 
                        background: dateRange.map((d, i) => 
                          isWeekend(d) ? `linear-gradient(90deg, rgba(0,0,0,0.03) ${i * dayWidth}px, rgba(0,0,0,0.03) ${(i + 1) * dayWidth}px)` : ''
                        ).join(', ')
                      }}
                    >
                      {/* Baseline Bar (if enabled) */}
                      {showBaseline && (
                        <div
                          className="absolute top-[8px] h-3 rounded bg-muted-foreground/20 border border-dashed border-muted-foreground/40"
                          style={{
                            left: task.baselineStartOffset * dayWidth,
                            width: Math.max(task.baselineDuration * dayWidth - 4, 20),
                          }}
                        />
                      )}
                      
                      {/* Main Task Bar */}
                      <div
                        className={`absolute top-1/2 -translate-y-1/2 h-7 rounded shadow-sm cursor-grab active:cursor-grabbing transition-all hover:h-8 hover:shadow-md ${
                          STATUS_COLORS[task.status]?.bg || 'bg-slate-400'
                        } ${
                          isCritical ? 'ring-2 ring-red-500 ring-offset-1' : ''
                        } border-l-4 ${
                          PRIORITY_COLORS[task.priority]?.border || 'border-slate-500'
                        }`}
                        style={{
                          left: displayTask.startOffset * dayWidth,
                          width: Math.max(displayTask.duration * dayWidth - 4, 30),
                        }}
                        onMouseDown={(e) => handleDragStart(e, task)}
                        onClick={(e) => {
                          if (!draggedTask) {
                            e.stopPropagation();
                            onTaskClick && onTaskClick(task);
                          }
                        }}
                      >
                        {/* Progress Fill */}
                        <div
                          className="h-full bg-white/30 rounded-l transition-all"
                          style={{ width: `${task.progress}%` }}
                        />
                        
                        {/* Task Label (if wide enough) */}
                        {displayTask.duration * dayWidth > 80 && (
                          <span className="absolute inset-0 flex items-center justify-center text-white text-xs font-medium truncate px-2">
                            {task.title}
                          </span>
                        )}
                        
                        {/* Drag handles */}
                        <div className="absolute left-0 top-0 bottom-0 w-2 cursor-ew-resize hover:bg-white/30 rounded-l" />
                        <div className="absolute right-0 top-0 bottom-0 w-2 cursor-ew-resize hover:bg-white/30 rounded-r" />
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Legend */}
            <div className="flex flex-wrap items-center gap-6 mt-4 pt-4 border-t border-border text-xs">
              <div className="flex items-center gap-3">
                <span className="text-muted-foreground font-medium">Status:</span>
                {Object.entries(STATUS_COLORS).map(([status, colors]) => (
                  <div key={status} className="flex items-center gap-1">
                    <div className={`w-3 h-3 rounded ${colors.bg}`} />
                    <span className="capitalize">{status.replace("_", " ")}</span>
                  </div>
                ))}
              </div>
              
              <div className="flex items-center gap-3">
                <span className="text-muted-foreground font-medium">Priority:</span>
                {Object.entries(PRIORITY_COLORS).map(([priority, colors]) => (
                  <div key={priority} className="flex items-center gap-1">
                    <div className={`w-3 h-3 rounded border-l-4 ${colors.border} bg-muted`} />
                    <span className="capitalize">{priority}</span>
                  </div>
                ))}
              </div>
              
              {showCriticalPath && (
                <div className="flex items-center gap-1">
                  <Zap className="w-3 h-3 text-red-500" />
                  <span className="text-red-500 font-medium">Critical Path</span>
                </div>
              )}
              
              {showBaseline && (
                <div className="flex items-center gap-1">
                  <div className="w-6 h-2 rounded border border-dashed border-muted-foreground/40 bg-muted-foreground/20" />
                  <span>Baseline</span>
                </div>
              )}
              
              {showDependencies && (
                <div className="flex items-center gap-2">
                  <ArrowRight className="w-3 h-3 text-muted-foreground" />
                  <span>Dependency</span>
                </div>
              )}
            </div>
            
            {/* Statistics */}
            <div className="flex flex-wrap gap-4 mt-4 pt-4 border-t border-border">
              <Badge variant="outline" className="text-xs">
                📊 Total Tasks: {tasks.length}
              </Badge>
              <Badge variant="outline" className="text-xs">
                ✅ Completed: {tasks.filter(t => t.status === 'done').length}
              </Badge>
              <Badge variant="outline" className="text-xs text-red-500 border-red-500">
                🔥 Critical: {criticalPath.size}
              </Badge>
              <Badge variant="outline" className="text-xs text-orange-500 border-orange-500">
                ⚠️ Blocked: {tasks.filter(t => (t.blocked_by || []).some(bid => tasks.find(bt => bt.task_id === bid)?.status !== 'done')).length}
              </Badge>
            </div>
          </div>
        </div>
        </div>
      </CardContent>
    </Card>
  );
};

export default GanttChart;
