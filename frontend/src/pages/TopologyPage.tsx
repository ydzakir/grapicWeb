import React, { useState, useMemo, useCallback } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  ReactFlow,
  Controls,
  Background,
  useNodesState,
  useEdgesState,
  Node as FlowNode,
  Edge as FlowEdge,
  Position,
  MarkerType,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import dagre from 'dagre';
import { apiClient } from '../services/apiClient';
import { TopologyGraph, MetricSeries } from '../types/api';
import {
  Server,
  Container,
  Database,
  Cpu,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  HelpCircle,
  X,
  RefreshCw,
  Layers,
} from 'lucide-react';
import { ResponsiveContainer, LineChart, Line, XAxis, YAxis, Tooltip, CartesianGrid } from 'recharts';

// Node Type Icons & Status Icons
const getNodeIcon = (type: string) => {
  switch (type) {
    case 'data_center':
      return <Database className="type-icon" />;
    case 'physical_server':
    case 'hyperv_host':
    case 'docker_host':
      return <Server className="type-icon" />;
    case 'hyperv_vm':
      return <Cpu className="type-icon" />;
    case 'docker_container':
      return <Container className="type-icon" />;
    default:
      return <Server className="type-icon" />;
  }
};

const getStatusBadge = (status: string) => {
  switch (status) {
    case 'up':
      return (
        <span className="status-badge-inline up">
          <CheckCircle2 className="status-icon" /> UP
        </span>
      );
    case 'warning':
      return (
        <span className="status-badge-inline warning">
          <AlertTriangle className="status-icon" /> WARN
        </span>
      );
    case 'down':
      return (
        <span className="status-badge-inline down">
          <XCircle className="status-icon" /> DOWN
        </span>
      );
    default:
      return (
        <span className="status-badge-inline unknown">
          <HelpCircle className="status-icon" /> UNK
        </span>
      );
  }
};

// Dagre Layout Algorithm
const getLayoutedElements = (nodes: FlowNode[], edges: FlowEdge[], direction = 'TB') => {
  const dagreGraph = new dagre.graphlib.Graph();
  dagreGraph.setDefaultEdgeLabel(() => ({}));
  dagreGraph.setGraph({ rankdir: direction, nodesep: 50, ranksep: 80 });

  nodes.forEach((node) => {
    dagreGraph.setNode(node.id, { width: 220, height: 90 });
  });

  edges.forEach((edge) => {
    dagreGraph.setEdge(edge.source, edge.target);
  });

  dagre.layout(dagreGraph);

  const layoutedNodes = nodes.map((node) => {
    const nodeWithPosition = dagreGraph.node(node.id);
    return {
      ...node,
      targetPosition: Position.Top,
      sourcePosition: Position.Bottom,
      position: {
        x: nodeWithPosition.x - 110,
        y: nodeWithPosition.y - 45,
      },
    };
  });

  return { nodes: layoutedNodes, edges };
};

export const TopologyPage: React.FC = () => {
  const [includePending, setIncludePending] = useState(false);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);

  // Fetch Topology Graph Data
  const {
    data: topologyData,
    isLoading,
    isError,
    refetch,
  } = useQuery<TopologyGraph>({
    queryKey: ['topology', includePending],
    queryFn: () => apiClient.get<TopologyGraph>(`/topology?include_pending=${includePending}`),
  });

  // Fetch metrics when node selected
  const { data: metricsData, isLoading: isLoadingMetrics } = useQuery<MetricSeries>({
    queryKey: ['metrics', selectedNodeId],
    queryFn: () => apiClient.get<MetricSeries>(`/metrics?node_id=${selectedNodeId}&metric_name=cpu_usage&range=1h`),
    enabled: !!selectedNodeId,
  });

  // Convert API Nodes & Edges to React Flow Layout
  const { nodes: flowNodes, edges: flowEdges } = useMemo(() => {
    if (!topologyData || !topologyData.nodes) {
      return { nodes: [], edges: [] };
    }

    const rawNodes: FlowNode[] = topologyData.nodes.map((node) => ({
      id: node.id,
      position: { x: 0, y: 0 },
      data: { nodeData: node },
      style: {
        background: '#1e293b',
        color: '#f8fafc',
        border: `2px solid ${
          node.status === 'up'
            ? '#10b981'
            : node.status === 'warning'
            ? '#f59e0b'
            : node.status === 'down'
            ? '#ef4444'
            : '#64748b'
        }`,
        borderRadius: '8px',
        padding: '10px 14px',
        width: 220,
      },
    }));

    const rawEdges: FlowEdge[] = topologyData.edges.map((edge) => ({
      id: edge.id,
      source: edge.source,
      target: edge.target,
      type: 'smoothstep',
      animated: edge.connection_type === 'network',
      style: { stroke: '#475569', strokeWidth: 2 },
      markerEnd: { type: MarkerType.ArrowClosed, color: '#475569' },
    }));

    return getLayoutedElements(rawNodes, rawEdges);
  }, [topologyData]);

  const [nodes, setNodes, onNodesChange] = useNodesState(flowNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(flowEdges);

  React.useEffect(() => {
    setNodes(flowNodes);
    setEdges(flowEdges);
  }, [flowNodes, flowEdges, setNodes, setEdges]);

  const onNodeClick = useCallback((_: any, node: FlowNode) => {
    setSelectedNodeId(node.id);
  }, []);

  const selectedNode = useMemo(() => {
    if (!selectedNodeId || !topologyData?.nodes) return null;
    return topologyData.nodes.find((n) => n.id === selectedNodeId) || null;
  }, [selectedNodeId, topologyData]);

  return (
    <div className="topology-page">
      <div className="topology-header">
        <div>
          <h1 className="page-title">Infrastructure Auto-Topology</h1>
          <p className="page-subtitle">Hierarchical infrastructure dependency graph</p>
        </div>

        <div className="topology-actions">
          <label className="toggle-label">
            <input
              type="checkbox"
              checked={includePending}
              onChange={(e) => setIncludePending(e.target.checked)}
            />
            <span>Include Pending Nodes</span>
          </label>

          <button onClick={() => refetch()} className="btn-secondary" title="Refresh Topology">
            <RefreshCw className="btn-icon" /> Refresh
          </button>
        </div>
      </div>

      {/* Status Legend Bar */}
      <div className="legend-bar">
        <span className="legend-title">Status Indicators:</span>
        <div className="legend-item"><CheckCircle2 className="status-icon icon-up" /> UP (Normal)</div>
        <div className="legend-item"><AlertTriangle className="status-icon icon-warning" /> WARNING (Resource High)</div>
        <div className="legend-item"><XCircle className="status-icon icon-down" /> DOWN (Offline)</div>
        <div className="legend-item"><HelpCircle className="status-icon icon-unknown" /> UNKNOWN (Unreachable)</div>
      </div>

      {/* Main Canvas Area */}
      <div className="canvas-wrapper">
        {isLoading ? (
          <div className="loading-state">
            <RefreshCw className="spin-icon" /> Loading topology graph...
          </div>
        ) : isError ? (
          <div className="error-state">
            <AlertTriangle className="error-icon" />
            <p>Failed to load topology graph from server.</p>
            <button onClick={() => refetch()} className="btn-primary">Retry</button>
          </div>
        ) : nodes.length === 0 ? (
          <div className="empty-state">
            <Layers className="empty-icon" />
            <p>No approved nodes found in topology.</p>
          </div>
        ) : (
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onNodeClick={onNodeClick}
            fitView
            fitViewOptions={{ padding: 0.2 }}
          >
            <Background color="#334155" gap={16} size={1} />
            <Controls />
          </ReactFlow>
        )}

        {/* Selected Node Details Side Panel */}
        {selectedNode && (
          <div className="node-detail-panel">
            <div className="panel-top">
              <div className="node-header">
                {getNodeIcon(selectedNode.type)}
                <div>
                  <h4>{selectedNode.name}</h4>
                  <span className="node-type-label">{selectedNode.type.replace('_', ' ')}</span>
                </div>
              </div>
              <button onClick={() => setSelectedNodeId(null)} className="btn-close">
                <X />
              </button>
            </div>

            <div className="panel-content">
              <div className="detail-section">
                <h5>Node Properties</h5>
                <div className="property-grid">
                  <div className="prop-item">
                    <span className="prop-label">Status</span>
                    {getStatusBadge(selectedNode.status)}
                  </div>
                  <div className="prop-item">
                    <span className="prop-label">IP Address</span>
                    <span className="prop-value">{selectedNode.ip_address || 'N/A'}</span>
                  </div>
                  <div className="prop-item">
                    <span className="prop-label">OS</span>
                    <span className="prop-value">{selectedNode.os || 'N/A'}</span>
                  </div>
                  <div className="prop-item">
                    <span className="prop-label">CPU Cores</span>
                    <span className="prop-value">{selectedNode.cpu_cores ? `${selectedNode.cpu_cores} cores` : 'N/A'}</span>
                  </div>
                  <div className="prop-item">
                    <span className="prop-label">RAM</span>
                    <span className="prop-value">{selectedNode.ram_mb ? `${Math.round(selectedNode.ram_mb / 1024)} GB` : 'N/A'}</span>
                  </div>
                  <div className="prop-item">
                    <span className="prop-label">Disk</span>
                    <span className="prop-value">{selectedNode.disk_gb ? `${selectedNode.disk_gb} GB` : 'N/A'}</span>
                  </div>
                </div>
              </div>

              {/* Time-Series Chart */}
              <div className="detail-section">
                <h5>CPU Usage (Last 1 Hour)</h5>
                <div className="chart-wrapper">
                  {isLoadingMetrics ? (
                    <div className="chart-loading">Loading metrics...</div>
                  ) : metricsData?.datapoints && metricsData.datapoints.length > 0 ? (
                    <ResponsiveContainer width="100%" height={160}>
                      <LineChart data={metricsData.datapoints}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                        <XAxis dataKey="timestamp" stroke="#94a3b8" tickFormatter={(t) => new Date(t * 1000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })} />
                        <YAxis stroke="#94a3b8" domain={[0, 100]} />
                        <Tooltip labelFormatter={(t) => new Date(t * 1000).toLocaleString()} formatter={(v: number) => [`${v.toFixed(1)}%`, 'CPU Usage']} />
                        <Line type="monotone" dataKey="value" stroke="#38bdf8" strokeWidth={2} dot={false} />
                      </LineChart>
                    </ResponsiveContainer>
                  ) : (
                    <div className="chart-empty">No telemetry data recorded.</div>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
