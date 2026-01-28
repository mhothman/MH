import { useCallback, useMemo } from 'react';
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  MarkerType,
  Handle,
  Position,
} from 'reactflow';
import 'reactflow/dist/style.css';
import { Badge } from './ui/badge';
import { CheckCircle2, Circle, AlertTriangle } from 'lucide-react';

const PRIORITY_COLORS = {
  low: '#22c55e',
  medium: '#eab308',
  high: '#f97316',
  urgent: '#ef4444',
};

const STATUS_COLORS = {
  todo: '#64748b',
  in_progress: '#3b82f6',
  review: '#a855f7',
  done: '#22c55e',
};

// Custom node component for tasks
const TaskNode = ({ data }) => {
  const isBlocked = data.isBlocked;
  const isDone = data.status === 'done';
  
  return (
    <div
      className={`px-4 py-3 rounded-lg border-2 shadow-md min-w-[180px] max-w-[220px] bg-card ${
        isBlocked ? 'border-orange-500' : isDone ? 'border-green-500' : 'border-border'
      }`}
      data-testid={`graph-node-${data.taskId}`}
    >
      {/* Handle for incoming edges (left side) */}
      <Handle 
        type="target" 
        position={Position.Left} 
        style={{ background: '#64748b', width: 8, height: 8 }} 
      />
      
      <div className="flex items-center gap-2 mb-1">
        {isDone ? (
          <CheckCircle2 className="w-4 h-4 text-green-500 flex-shrink-0" />
        ) : isBlocked ? (
          <AlertTriangle className="w-4 h-4 text-orange-500 flex-shrink-0" />
        ) : (
          <Circle className="w-4 h-4 text-muted-foreground flex-shrink-0" />
        )}
        <span className="font-medium text-sm truncate">{data.title}</span>
      </div>
      <div className="flex items-center gap-2 mt-2">
        <Badge 
          variant="outline" 
          className="text-[10px]"
          style={{ borderColor: STATUS_COLORS[data.status] || '#64748b' }}
        >
          {data.statusLabel || data.status}
        </Badge>
        <div 
          className="w-2 h-2 rounded-full" 
          style={{ backgroundColor: PRIORITY_COLORS[data.priority] || '#64748b' }}
          title={data.priority}
        />
      </div>
      {data.assigneeName && (
        <div className="text-[10px] text-muted-foreground mt-1 truncate">
          {data.assigneeName}
        </div>
      )}
      
      {/* Handle for outgoing edges (right side) */}
      <Handle 
        type="source" 
        position={Position.Right} 
        style={{ background: '#64748b', width: 8, height: 8 }} 
      />
    </div>
  );
};

// Define nodeTypes outside component to avoid re-creation on every render
const nodeTypes = {
  task: TaskNode,
};

// Auto-layout algorithm (simple layered layout)
const getLayoutedElements = (tasks, taskStatuses) => {
  // Build adjacency list for topological sorting
  const taskMap = new Map(tasks.map(t => [t.task_id, t]));
  const inDegree = new Map();
  const adjacency = new Map();
  
  tasks.forEach(t => {
    inDegree.set(t.task_id, 0);
    adjacency.set(t.task_id, []);
  });
  
  // Build graph from blocked_by relationships
  tasks.forEach(task => {
    (task.blocked_by || []).forEach(blockerId => {
      if (taskMap.has(blockerId)) {
        adjacency.get(blockerId).push(task.task_id);
        inDegree.set(task.task_id, (inDegree.get(task.task_id) || 0) + 1);
      }
    });
  });
  
  // Assign layers using BFS (topological order)
  const layers = new Map();
  const queue = [];
  
  // Start with nodes that have no dependencies
  tasks.forEach(t => {
    if ((inDegree.get(t.task_id) || 0) === 0) {
      queue.push(t.task_id);
      layers.set(t.task_id, 0);
    }
  });
  
  while (queue.length > 0) {
    const taskId = queue.shift();
    const currentLayer = layers.get(taskId) || 0;
    
    (adjacency.get(taskId) || []).forEach(dependentId => {
      const newLayer = currentLayer + 1;
      layers.set(dependentId, Math.max(layers.get(dependentId) || 0, newLayer));
      
      const newInDegree = (inDegree.get(dependentId) || 1) - 1;
      inDegree.set(dependentId, newInDegree);
      
      if (newInDegree === 0) {
        queue.push(dependentId);
      }
    });
  }
  
  // Handle orphaned nodes (no dependencies at all)
  tasks.forEach(t => {
    if (!layers.has(t.task_id)) {
      layers.set(t.task_id, 0);
    }
  });
  
  // Group tasks by layer
  const layerGroups = new Map();
  tasks.forEach(t => {
    const layer = layers.get(t.task_id) || 0;
    if (!layerGroups.has(layer)) {
      layerGroups.set(layer, []);
    }
    layerGroups.get(layer).push(t);
  });
  
  // Calculate positions
  const nodeSpacingX = 280;
  const nodeSpacingY = 120;
  const nodes = [];
  
  const sortedLayers = Array.from(layerGroups.keys()).sort((a, b) => a - b);
  
  sortedLayers.forEach(layer => {
    const layerTasks = layerGroups.get(layer);
    const layerHeight = layerTasks.length * nodeSpacingY;
    const startY = -layerHeight / 2;
    
    layerTasks.forEach((task, index) => {
      const statusConfig = taskStatuses?.find(s => s.id === task.status);
      const isBlocked = (task.blocked_by || []).some(blockerId => {
        const blocker = taskMap.get(blockerId);
        return blocker && blocker.status !== 'done';
      });
      
      nodes.push({
        id: task.task_id,
        type: 'task',
        position: { x: layer * nodeSpacingX, y: startY + index * nodeSpacingY },
        data: {
          taskId: task.task_id,
          title: task.title,
          status: task.status,
          statusLabel: statusConfig?.label || task.status,
          priority: task.priority,
          isBlocked,
        },
      });
    });
  });
  
  // Create edges
  const edges = [];
  tasks.forEach(task => {
    (task.blocked_by || []).forEach(blockerId => {
      if (taskMap.has(blockerId)) {
        const blockerTask = taskMap.get(blockerId);
        const isBlockerDone = blockerTask?.status === 'done';
        
        edges.push({
          id: `${blockerId}-${task.task_id}`,
          source: blockerId,
          target: task.task_id,
          type: 'smoothstep',
          animated: !isBlockerDone,
          style: { 
            stroke: isBlockerDone ? '#22c55e' : '#f97316',
            strokeWidth: 2,
          },
          markerEnd: {
            type: MarkerType.ArrowClosed,
            color: isBlockerDone ? '#22c55e' : '#f97316',
          },
        });
      }
    });
  });
  
  return { nodes, edges };
};

export const DependencyGraph = ({ tasks, taskStatuses, onTaskClick }) => {
  const { nodes: initialNodes, edges: initialEdges } = useMemo(
    () => getLayoutedElements(tasks, taskStatuses),
    [tasks, taskStatuses]
  );
  
  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);
  
  const onNodeClick = useCallback((event, node) => {
    if (onTaskClick) {
      const task = tasks.find(t => t.task_id === node.id);
      if (task) onTaskClick(task);
    }
  }, [tasks, onTaskClick]);
  
  // Count dependencies
  const dependencyCount = edges.length;
  const blockedCount = tasks.filter(t => 
    (t.blocked_by || []).some(blockerId => {
      const blocker = tasks.find(bt => bt.task_id === blockerId);
      return blocker && blocker.status !== 'done';
    })
  ).length;
  
  if (tasks.length === 0) {
    return (
      <div className="flex items-center justify-center h-[400px] text-muted-foreground">
        No tasks to display
      </div>
    );
  }
  
  if (dependencyCount === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-[400px] text-muted-foreground">
        <p className="mb-2">No dependencies defined yet</p>
        <p className="text-sm">Open a task and add dependencies in the Dependencies section</p>
      </div>
    );
  }
  
  return (
    <div className="space-y-4" data-testid="dependency-graph">
      <div className="flex items-center gap-4 text-sm">
        <div className="flex items-center gap-2">
          <div className="w-8 h-0.5 bg-orange-500" />
          <span className="text-muted-foreground">Blocking (in progress)</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-8 h-0.5 bg-green-500" />
          <span className="text-muted-foreground">Resolved (done)</span>
        </div>
        <div className="ml-auto flex items-center gap-4">
          <Badge variant="outline">{dependencyCount} dependencies</Badge>
          {blockedCount > 0 && (
            <Badge variant="destructive">{blockedCount} blocked tasks</Badge>
          )}
        </div>
      </div>
      
      <div className="h-[500px] border border-border rounded-lg overflow-hidden bg-muted/20">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onNodeClick={onNodeClick}
          nodeTypes={nodeTypes}
          fitView
          fitViewOptions={{ padding: 0.2 }}
          minZoom={0.5}
          maxZoom={1.5}
        >
          <Background color="#888" gap={16} size={1} />
          <Controls showInteractive={false} />
          <MiniMap 
            nodeColor={(node) => {
              if (node.data?.isBlocked) return '#f97316';
              if (node.data?.status === 'done') return '#22c55e';
              return '#64748b';
            }}
            maskColor="rgba(0, 0, 0, 0.2)"
          />
        </ReactFlow>
      </div>
    </div>
  );
};

export default DependencyGraph;
