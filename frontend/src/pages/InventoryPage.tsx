import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../services/apiClient';
import { PaginatedNodes, NodeItem } from '../types/api';
import { useAuth } from '../context/AuthContext';
import {
  Search,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  HelpCircle,
  Check,
  X,
  Archive,
  RefreshCw,
  AlertCircle,
  Clock,
} from 'lucide-react';

export const InventoryPage: React.FC = () => {
  const { isAdmin } = useAuth();
  const queryClient = useQueryClient();

  const [page, setPage] = useState(1);
  const [pageSize] = useState(15);
  const [search, setSearch] = useState('');
  const [typeFilter, setTypeFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [reviewFilter, setReviewFilter] = useState('');
  const [lifecycleFilter, setLifecycleFilter] = useState('active');

  // Modal State for Approve Node
  const [approveModalNode, setApproveModalNode] = useState<NodeItem | null>(null);
  const [customName, setCustomName] = useState('');
  const [actionError, setActionError] = useState<string | null>(null);

  // Fetch paginated nodes
  const queryUrl = `/nodes?page=${page}&page_size=${pageSize}` +
    (search ? `&search=${encodeURIComponent(search)}` : '') +
    (typeFilter ? `&type=${typeFilter}` : '') +
    (statusFilter ? `&status=${statusFilter}` : '') +
    (reviewFilter ? `&review_status=${reviewFilter}` : '') +
    (lifecycleFilter ? `&lifecycle_status=${lifecycleFilter}` : '');

  const { data, isLoading, isError, refetch } = useQuery<PaginatedNodes>({
    queryKey: ['nodes', page, search, typeFilter, statusFilter, reviewFilter, lifecycleFilter],
    queryFn: () => apiClient.get<PaginatedNodes>(queryUrl),
  });

  // Approve Mutation
  const approveMutation = useMutation({
    mutationFn: ({ id, name }: { id: string; name?: string }) =>
      apiClient.post<NodeItem>(`/nodes/${id}/approve`, { name }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['nodes'] });
      setApproveModalNode(null);
      setActionError(null);
    },
    onError: (err: any) => {
      setActionError(err.message || 'Failed to approve node');
    },
  });

  // Reject Mutation
  const rejectMutation = useMutation({
    mutationFn: (id: string) => apiClient.post<NodeItem>(`/nodes/${id}/reject`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['nodes'] });
    },
  });

  // Archive Mutation
  const archiveMutation = useMutation({
    mutationFn: (id: string) => apiClient.post<NodeItem>(`/nodes/${id}/archive`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['nodes'] });
    },
  });

  const handleOpenApproveModal = (node: NodeItem) => {
    setApproveModalNode(node);
    setCustomName(node.name);
    setActionError(null);
  };

  const handleConfirmApprove = () => {
    if (!approveModalNode) return;
    approveMutation.mutate({ id: approveModalNode.id, name: customName });
  };

  const renderStatusBadge = (status: string) => {
    switch (status) {
      case 'up':
        return <span className="badge badge-up"><CheckCircle2 className="badge-icon" /> UP</span>;
      case 'warning':
        return <span className="badge badge-warning"><AlertTriangle className="badge-icon" /> WARN</span>;
      case 'down':
        return <span className="badge badge-down"><XCircle className="badge-icon" /> DOWN</span>;
      default:
        return <span className="badge badge-unknown"><HelpCircle className="badge-icon" /> UNKNOWN</span>;
    }
  };

  return (
    <div className="page-container">
      <header className="page-header">
        <div>
          <h1 className="page-title">Infrastructure Inventory</h1>
          <p className="page-subtitle">Managed servers, hypervisors, VMs, and container inventory</p>
        </div>
        <button onClick={() => refetch()} className="btn-secondary">
          <RefreshCw className="btn-icon" /> Refresh
        </button>
      </header>

      {/* Search & Filter Toolbar */}
      <div className="toolbar-panel">
        <div className="search-box">
          <Search className="search-icon" />
          <input
            type="text"
            placeholder="Search by name, IP, or OS..."
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setPage(1);
            }}
          />
        </div>

        <div className="filter-group">
          <select
            value={typeFilter}
            onChange={(e) => { setTypeFilter(e.target.value); setPage(1); }}
            className="filter-select"
          >
            <option value="">All Node Types</option>
            <option value="physical_server">Physical Server</option>
            <option value="hyperv_host">Hyper-V Host</option>
            <option value="docker_host">Docker Host</option>
            <option value="hyperv_vm">Hyper-V VM</option>
            <option value="docker_container">Docker Container</option>
          </select>

          <select
            value={statusFilter}
            onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }}
            className="filter-select"
          >
            <option value="">All Statuses</option>
            <option value="up">UP</option>
            <option value="warning">WARNING</option>
            <option value="down">DOWN</option>
            <option value="unknown">UNKNOWN</option>
          </select>

          <select
            value={reviewFilter}
            onChange={(e) => { setReviewFilter(e.target.value); setPage(1); }}
            className="filter-select"
          >
            <option value="">All Review Statuses</option>
            <option value="pending">Pending Review</option>
            <option value="approved">Approved</option>
            <option value="rejected">Rejected</option>
          </select>

          <select
            value={lifecycleFilter}
            onChange={(e) => { setLifecycleFilter(e.target.value); setPage(1); }}
            className="filter-select"
          >
            <option value="active">Active Only</option>
            <option value="archived">Archived</option>
            <option value="">All Lifecycles</option>
          </select>
        </div>
      </div>

      {/* Inventory Table */}
      <div className="table-container">
        {isLoading ? (
          <div className="loading-state">Loading inventory records...</div>
        ) : isError ? (
          <div className="error-state">
            <AlertCircle className="error-icon" />
            <p>Error loading inventory from server.</p>
            <button onClick={() => refetch()} className="btn-primary">Retry</button>
          </div>
        ) : !data?.items || data.items.length === 0 ? (
          <div className="empty-state">No matching infrastructure nodes found.</div>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th>Node Name</th>
                <th>Type</th>
                <th>Status</th>
                <th>Review Status</th>
                <th>IP Address</th>
                <th>OS &amp; Specs</th>
                <th>Last Seen</th>
                {isAdmin && <th>Admin Actions</th>}
              </tr>
            </thead>
            <tbody>
              {data.items.map((node) => (
                <tr key={node.id} className={node.review_status === 'pending' ? 'row-pending' : ''}>
                  <td>
                    <div className="node-name-cell">
                      <span className="node-name-text">{node.name}</span>
                      {node.review_status === 'pending' && (
                        <span className="badge badge-pending-review" style={{ backgroundColor: 'rgba(245, 158, 11, 0.15)', color: '#d97706', border: '1px solid rgba(245, 158, 11, 0.3)', fontSize: '0.75rem', padding: '2px 8px', borderRadius: '12px', marginLeft: '8px', display: 'inline-flex', alignItems: 'center', gap: '4px', fontWeight: 600 }}>
                          <Clock className="badge-icon" style={{ width: '12px', height: '12px' }} /> Pending Review
                        </span>
                      )}
                      {node.metadata?.validation_issue && (
                        <span className="validation-issue-tag" title={node.metadata.validation_issue}>
                          <AlertTriangle className="tag-icon" /> Invalid Name Format
                        </span>
                      )}
                    </div>
                  </td>
                  <td>
                    <span className="type-tag">{node.type.replace('_', ' ')}</span>
                  </td>
                  <td>{renderStatusBadge(node.status)}</td>
                  <td>
                    <span className={`review-tag ${node.review_status}`}>
                      {node.review_status}
                    </span>
                  </td>
                  <td>{node.ip_address || 'N/A'}</td>
                  <td>
                    <div className="specs-cell">
                      <span>{node.os || 'OS Unspecified'}</span>
                      <small>
                        {node.cpu_cores ? `${node.cpu_cores}C` : ''}{' '}
                        {node.ram_mb ? `${Math.round(node.ram_mb / 1024)}GB` : ''}
                      </small>
                    </div>
                  </td>
                  <td>
                    {node.last_seen
                      ? new Date(node.last_seen).toLocaleString()
                      : 'Never'}
                  </td>
                  {isAdmin && (
                    <td>
                      <div className="action-buttons">
                        {node.review_status === 'pending' && (
                          <>
                            <button
                              onClick={() => handleOpenApproveModal(node)}
                              className="btn-icon-action btn-approve"
                              title="Approve Node"
                            >
                              <Check className="action-icon" /> Approve
                            </button>
                            <button
                              onClick={() => rejectMutation.mutate(node.id)}
                              className="btn-icon-action btn-reject"
                              title="Reject Node"
                            >
                              <X className="action-icon" />
                            </button>
                          </>
                        )}
                        {node.lifecycle_status === 'active' && (
                          <button
                            onClick={() => archiveMutation.mutate(node.id)}
                            className="btn-icon-action btn-archive"
                            title="Archive Node"
                          >
                            <Archive className="action-icon" />
                          </button>
                        )}
                      </div>
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        )}

        {/* Pagination Footer */}
        {data && data.total > 0 && (
          <div className="pagination-footer">
            <span>
              Showing {((page - 1) * pageSize) + 1} - {Math.min(page * pageSize, data.total)} of {data.total} items
            </span>
            <div className="pagination-buttons">
              <button
                disabled={page <= 1}
                onClick={() => setPage((p) => p - 1)}
                className="btn-secondary btn-sm"
              >
                Previous
              </button>
              <span className="page-num">Page {page}</span>
              <button
                disabled={page * pageSize >= data.total}
                onClick={() => setPage((p) => p + 1)}
                className="btn-secondary btn-sm"
              >
                Next
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Admin Approval Modal */}
      {approveModalNode && (
        <div className="modal-overlay">
          <div className="modal-card">
            <h3>Approve Host Node</h3>
            <p>Verify or adjust the host name to match convention <code>[TYPE]-[LOKASI]-[FUNGSI]-[NOMOR]</code> (e.g. <code>HYPERV-DC1-WEB-01</code>).</p>

            {actionError && (
              <div className="alert-error">
                <AlertCircle className="alert-icon" />
                <span>{actionError}</span>
              </div>
            )}

            <div className="form-group">
              <label>Host Name</label>
              <input
                type="text"
                value={customName}
                onChange={(e) => setCustomName(e.target.value)}
                placeholder="e.g. DOCKER-DC1-APP-01"
              />
            </div>

            <div className="modal-actions">
              <button onClick={() => setApproveModalNode(null)} className="btn-secondary">
                Cancel
              </button>
              <button
                onClick={handleConfirmApprove}
                className="btn-primary"
                disabled={approveMutation.isPending}
              >
                {approveMutation.isPending ? 'Approving...' : 'Confirm Approval'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
