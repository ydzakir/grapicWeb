import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../services/apiClient';
import { PaginatedNodes, TopologyGraph } from '../types/api';
import { Server, Container, AlertTriangle, ShieldCheck } from 'lucide-react';
import { Link } from 'react-router-dom';
import { CloudflareEdgeCard } from '../components/CloudflareEdgeCard';

export const DashboardPage: React.FC = () => {

  // Query all active nodes for summary statistics
  const { data: nodesData, isLoading: isLoadingNodes } = useQuery<PaginatedNodes>({
    queryKey: ['nodes', 'summary'],
    queryFn: () => apiClient.get<PaginatedNodes>('/nodes?page=1&page_size=100&lifecycle_status=active'),
  });

  // Query topology graph for mini-overview
  const { data: topologyData, isLoading: isLoadingTopology } = useQuery<TopologyGraph>({
    queryKey: ['topology', 'mini'],
    queryFn: () => apiClient.get<TopologyGraph>('/topology'),
  });

  const items = nodesData?.items || [];

  // Only approved, active inventory counts toward summary (pending nodes excluded)
  const approvedItems = items.filter((n) => n.review_status === 'approved');

  // Servers = physical + hypervisor + docker hosts (VMs and containers excluded)
  const totalServers = approvedItems.filter(
    (n) => n.type === 'physical_server' || n.type === 'hyperv_host' || n.type === 'docker_host'
  ).length;

  const totalContainers = approvedItems.filter((n) => n.type === 'docker_container').length;

  const unhealthyNodes = approvedItems.filter((n) => n.status === 'down' || n.status === 'warning');

  const pendingApprovals = items.filter((n) => n.review_status === 'pending').length;

  return (
    <div className="page-container">
      <header className="page-header">
        <div>
          <h1 className="page-title">Infrastructure Overview</h1>
          <p className="page-subtitle">Real-time telemetry and topology overview</p>
        </div>
      </header>

      {/* Summary Stat Cards */}
      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-header">
            <span className="stat-title">Servers &amp; Hosts</span>
            <Server className="stat-icon icon-blue" />
          </div>
          <div className="stat-value">{isLoadingNodes ? '...' : totalServers}</div>
          <div className="stat-description">Physical servers, Hyper-V &amp; Docker hosts</div>
        </div>

        <div className="stat-card">
          <div className="stat-header">
            <span className="stat-title">Containers</span>
            <Container className="stat-icon icon-purple" />
          </div>
          <div className="stat-value">{isLoadingNodes ? '...' : totalContainers}</div>
          <div className="stat-description">Managed Docker container instances</div>
        </div>

        <div className="stat-card">
          <div className="stat-header">
            <span className="stat-title">Unhealthy Nodes</span>
            <AlertTriangle className="stat-icon icon-red" />
          </div>
          <div className="stat-value">{isLoadingNodes ? '...' : unhealthyNodes.length}</div>
          <div className="stat-description">Nodes in Down or Warning state</div>
        </div>

        <div className="stat-card">
          <div className="stat-header">
            <span className="stat-title">Pending Review</span>
            <ShieldCheck className="stat-icon icon-amber" />
          </div>
          <div className="stat-value">{isLoadingNodes ? '...' : pendingApprovals}</div>
          <div className="stat-description">Nodes awaiting admin approval</div>
        </div>
      </div>

      {/* Cloudflare Edge Status Integration Card */}
      <div className="mb-6">
        <CloudflareEdgeCard />
      </div>

      {/* Main Grid: Mini Topology & Unhealthy List */}
      <div className="dashboard-grid">

        <div className="panel flex-2">
          <div className="panel-header">
            <h3>Infrastructure Topology Preview</h3>
            <Link to="/topology" className="btn-link">View Interactive Canvas →</Link>
          </div>
          <div className="panel-body mini-topology-box">
            {isLoadingTopology ? (
              <div className="loading-state">Loading topology overview...</div>
            ) : topologyData?.nodes && topologyData.nodes.length > 0 ? (
              <div className="mini-nodes-grid">
                {topologyData.nodes.map((node) => (
                  <div key={node.id} className={`mini-node-pill ${node.status}`}>
                    <span className="mini-node-name">{node.name}</span>
                    <span className="mini-node-type">{node.type.replace('_', ' ')}</span>
                  </div>
                ))}
              </div>
            ) : (
              <div className="empty-state">No approved nodes found in topology.</div>
            )}
          </div>
        </div>

        <div className="panel flex-1">
          <div className="panel-header">
            <h3>Attention Needed</h3>
          </div>
          <div className="panel-body">
            {unhealthyNodes.length > 0 ? (
              <ul className="unhealthy-list">
                {unhealthyNodes.map((n) => (
                  <li key={n.id} className={`unhealthy-item ${n.status}`}>
                    <div className="unhealthy-info">
                      <span className="unhealthy-name">{n.name}</span>
                      <span className="unhealthy-ip">{n.ip_address || 'No IP'}</span>
                    </div>
                    <span className={`status-badge ${n.status}`}>{n.status.toUpperCase()}</span>
                  </li>
                ))}
              </ul>
            ) : (
              <div className="empty-state-success">
                <ShieldCheck className="success-icon" />
                <p>All monitored infrastructure nodes are healthy.</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
