import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../services/apiClient';
import { CollectorTarget, DataCenter, PaginatedNodes } from '../types/api';
import {
  Server,
  Plus,
  Zap,
  Building2,
  CheckCircle2,
  AlertCircle,
  ShieldAlert,
  Check,
  FileText,
  Download,
} from 'lucide-react';

export const AdministrationPage: React.FC = () => {
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState<'collectors' | 'datacenters' | 'pending' | 'reports'>('collectors');
  const [reportType, setReportType] = useState<'weekly' | 'monthly'>('weekly');
  const [reportFormat, setReportFormat] = useState<'pdf' | 'excel'>('pdf');
  const [isGeneratingReport, setIsGeneratingReport] = useState(false);

  // Collector Targets State
  const [isAddTargetModalOpen, setIsAddTargetModalOpen] = useState(false);
  const [targetName, setTargetName] = useState('');
  const [targetType, setTargetType] = useState<'ssh' | 'winrm' | 'hyperv' | 'docker'>('ssh');
  const [hostUrl, setHostUrl] = useState('');
  const [port, setPort] = useState<number | ''>('');
  const [credRef, setCredRef] = useState('');
  const [testResult, setTestResult] = useState<{ id: string; status: string; message: string } | null>(null);

  // Data Center State
  const [isAddDcModalOpen, setIsAddDcModalOpen] = useState(false);
  const [dcName, setDcName] = useState('');
  const [dcLocation, setDcLocation] = useState('');
  const [assignDcId, setAssignDcId] = useState<string | null>(null);
  const [selectedHostIds, setSelectedHostIds] = useState<string[]>([]);

  // Fetch Collector Targets
  const { data: targets, isLoading: isLoadingTargets } = useQuery<CollectorTarget[]>({
    queryKey: ['collector-targets'],
    queryFn: () => apiClient.get<CollectorTarget[]>('/collectors/targets'),
  });

  // Fetch Data Centers
  const { data: dataCenters, isLoading: isLoadingDCs } = useQuery<DataCenter[]>({
    queryKey: ['datacenters'],
    queryFn: () => apiClient.get<DataCenter[]>('/datacenters'),
  });

  // Fetch Approved Hosts for DC Assignment
  const { data: approvedHosts } = useQuery<PaginatedNodes>({
    queryKey: ['nodes', 'approved-hosts'],
    queryFn: () => apiClient.get<PaginatedNodes>('/nodes?review_status=approved&page_size=100'),
    enabled: !!assignDcId,
  });

  // Fetch Pending Nodes Queue
  const { data: pendingNodes } = useQuery<PaginatedNodes>({
    queryKey: ['nodes', 'pending-queue'],
    queryFn: () => apiClient.get<PaginatedNodes>('/nodes?review_status=pending&page_size=100'),
    enabled: activeTab === 'pending',
  });

  // Create Collector Target Mutation
  const createTargetMutation = useMutation({
    mutationFn: (body: any) => apiClient.post<CollectorTarget>('/collectors/targets', body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['collector-targets'] });
      setIsAddTargetModalOpen(false);
      resetTargetForm();
    },
  });

  // Test Connection Mutation
  const testConnectionMutation = useMutation({
    mutationFn: (targetId: string) =>
      apiClient.post<{ status: string; message: string }>(`/collectors/targets/${targetId}/test-connection`),
    onSuccess: (data, targetId) => {
      setTestResult({ id: targetId, status: data.status, message: data.message });
      queryClient.invalidateQueries({ queryKey: ['collector-targets'] });
    },
  });

  // Create Data Center Mutation
  const createDcMutation = useMutation({
    mutationFn: (body: any) => apiClient.post<DataCenter>('/datacenters', body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['datacenters'] });
      setIsAddDcModalOpen(false);
      setDcName('');
      setDcLocation('');
    },
  });

  // Assign Hosts Mutation
  const assignHostsMutation = useMutation({
    mutationFn: ({ dcId, hostIds }: { dcId: string; hostIds: string[] }) =>
      apiClient.post(`/datacenters/${dcId}/assign-hosts`, { host_ids: hostIds }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['nodes'] });
      queryClient.invalidateQueries({ queryKey: ['topology'] });
      setAssignDcId(null);
      setSelectedHostIds([]);
    },
  });

  // Approve Node Mutation
  const approveNodeMutation = useMutation({
    mutationFn: (id: string) => apiClient.post(`/nodes/${id}/approve`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['nodes'] });
    },
  });

  const resetTargetForm = () => {
    setTargetName('');
    setTargetType('ssh');
    setHostUrl('');
    setPort('');
    setCredRef('');
  };

  const handleCreateTarget = (e: React.FormEvent) => {
    e.preventDefault();
    createTargetMutation.mutate({
      name: targetName,
      target_type: targetType,
      host_or_url: hostUrl,
      port: port ? Number(port) : null,
      credential_reference: credRef,
      poll_interval_seconds: 60,
    });
  };

  const handleCreateDC = (e: React.FormEvent) => {
    e.preventDefault();
    createDcMutation.mutate({ name: dcName, location: dcLocation });
  };

  const handleAssignHostsSubmit = () => {
    if (!assignDcId) return;
    assignHostsMutation.mutate({ dcId: assignDcId, hostIds: selectedHostIds });
  };

  const handleGenerateReport = async () => {
    setIsGeneratingReport(true);
    try {
      const res = await apiClient.post<{ filename: string; download_url: string }>('/reports/generate', {
        report_type: reportType,
        format: reportFormat,
      });

      // Trigger automatic file download
      const link = document.createElement('a');
      link.href = res.download_url;
      link.setAttribute('download', res.filename);
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch (err) {
      alert('Failed to generate report.');
    } finally {
      setIsGeneratingReport(false);
    }
  };

  return (
    <div className="page-container">
      <header className="page-header">
        <div>
          <h1 className="page-title">Administration</h1>
          <p className="page-subtitle">Manage collector targets, data centers, and approval queue</p>
        </div>
      </header>

      {/* Admin Tabs */}
      <div className="admin-tabs">
        <button
          className={`tab-btn ${activeTab === 'collectors' ? 'active' : ''}`}
          onClick={() => setActiveTab('collectors')}
        >
          <Server className="tab-icon" /> Collector Targets
        </button>

        <button
          className={`tab-btn ${activeTab === 'datacenters' ? 'active' : ''}`}
          onClick={() => setActiveTab('datacenters')}
        >
          <Building2 className="tab-icon" /> Data Centers
        </button>

        <button
          className={`tab-btn ${activeTab === 'pending' ? 'active' : ''}`}
          onClick={() => setActiveTab('pending')}
        >
          <ShieldAlert className="tab-icon" /> Pending Approvals Queue
        </button>

        <button
          className={`tab-btn ${activeTab === 'reports' ? 'active' : ''}`}
          onClick={() => setActiveTab('reports')}
        >
          <FileText className="tab-icon" /> Executive Reports
        </button>
      </div>

      {/* Tab 1: Collector Targets */}
      {activeTab === 'collectors' && (
        <div className="tab-content">
          <div className="tab-header">
            <h3>Registered Collector Targets</h3>
            <button onClick={() => setIsAddTargetModalOpen(true)} className="btn-primary">
              <Plus className="btn-icon" /> Add Collector Target
            </button>
          </div>

          {isLoadingTargets ? (
            <div className="loading-state">Loading collector targets...</div>
          ) : !targets || targets.length === 0 ? (
            <div className="empty-state">No collector targets registered yet.</div>
          ) : (
            <div className="cards-grid">
              {targets.map((target) => (
                <div key={target.id} className="target-card">
                  <div className="card-header">
                    <h4>{target.name}</h4>
                    <span className="type-tag">{target.target_type.toUpperCase()}</span>
                  </div>
                  <div className="card-body">
                    <div className="info-row">
                      <span className="label">Host / Endpoint:</span>
                      <span className="val">{target.host_or_url}</span>
                    </div>
                    <div className="info-row">
                      <span className="label">Cred Reference:</span>
                      <span className="val badge-ref">{target.credential_reference}</span>
                    </div>
                    <div className="info-row">
                      <span className="label">Poll Interval:</span>
                      <span className="val">{target.poll_interval_seconds}s</span>
                    </div>
                    {(testResult?.id === target.id ? testResult.status : target.last_test_status) && (
                      <div className={`test-status-banner ${testResult?.id === target.id ? testResult.status : target.last_test_status}`}>
                        {(testResult?.id === target.id ? testResult.status : target.last_test_status) === 'success' ? (
                          <CheckCircle2 className="status-icon" />
                        ) : (
                          <AlertCircle className="status-icon" />
                        )}
                        <span>{testResult?.id === target.id ? testResult.message : (target.last_test_message || target.last_test_status)}</span>
                      </div>
                    )}
                  </div>
                  <div className="card-footer">
                    <button
                      onClick={() => testConnectionMutation.mutate(target.id)}
                      className="btn-secondary btn-block"
                      disabled={testConnectionMutation.isPending}
                    >
                      <Zap className="btn-icon" /> Test Connection
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Tab 2: Data Centers */}
      {activeTab === 'datacenters' && (
        <div className="tab-content">
          <div className="tab-header">
            <h3>Data Center Groups</h3>
            <button onClick={() => setIsAddDcModalOpen(true)} className="btn-primary">
              <Plus className="btn-icon" /> Create Data Center
            </button>
          </div>

          {isLoadingDCs ? (
            <div className="loading-state">Loading data centers...</div>
          ) : !dataCenters || dataCenters.length === 0 ? (
            <div className="empty-state">No Data Centers created.</div>
          ) : (
            <div className="cards-grid">
              {dataCenters.map((dc) => (
                <div key={dc.id} className="dc-card">
                  <div className="card-header">
                    <Building2 className="dc-icon" />
                    <h4>{dc.name}</h4>
                  </div>
                  <div className="card-body">
                    <p className="dc-location">Location: {dc.metadata?.location || 'Unspecified'}</p>
                  </div>
                  <div className="card-footer">
                    <button
                      onClick={() => {
                        setAssignDcId(dc.id);
                        setSelectedHostIds([]);
                      }}
                      className="btn-secondary btn-block"
                    >
                      Assign Hosts
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Tab 3: Pending Queue */}
      {activeTab === 'pending' && (
        <div className="tab-content">
          <div className="tab-header">
            <h3>Pending Review Queue</h3>
          </div>
          {!pendingNodes?.items || pendingNodes.items.length === 0 ? (
            <div className="empty-state-success">
              <CheckCircle2 className="success-icon" />
              <p>No pending nodes awaiting approval.</p>
            </div>
          ) : (
            <div className="table-container">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Discovered Node Name</th>
                    <th>Type</th>
                    <th>IP Address</th>
                    <th>Discovered OS</th>
                    <th>Validation Check</th>
                    <th>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {pendingNodes.items.map((node) => (
                    <tr key={node.id}>
                      <td>{node.name}</td>
                      <td><span className="type-tag">{node.type.replace('_', ' ')}</span></td>
                      <td>{node.ip_address || 'N/A'}</td>
                      <td>{node.os || 'N/A'}</td>
                      <td>
                        {node.metadata?.validation_issue ? (
                          <span className="validation-issue-tag">
                            <AlertCircle className="tag-icon" /> {node.metadata.validation_issue}
                          </span>
                        ) : (
                          <span className="validation-ok-tag">Valid Host Name</span>
                        )}
                      </td>
                      <td>
                        <button
                          onClick={() => approveNodeMutation.mutate(node.id)}
                          className="btn-icon-action btn-approve"
                        >
                          <Check className="action-icon" /> Approve
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Tab 4: Executive Reports */}
      {activeTab === 'reports' && (
        <div className="tab-content">
          <div className="tab-header">
            <h3>Generate Executive Reports</h3>
          </div>

          <div className="target-card report-generator-card">
            <div className="card-header">
              <h4>Periodic Infrastructure Summary Report</h4>
            </div>
            <div className="card-body">
              <p className="card-desc">
                Generate formatted PDF or Excel executive reports summarizing SLA availability, asset inventory, and recent alert incident history.
              </p>

              <div className="form-grid">
                <div className="form-group">
                  <label>Report Time Period</label>
                  <select value={reportType} onChange={(e) => setReportType(e.target.value as any)}>
                    <option value="weekly">Weekly Recap Report (Last 7 Days)</option>
                    <option value="monthly">Monthly Executive Report (Last 30 Days)</option>
                  </select>
                </div>

                <div className="form-group">
                  <label>Export File Format</label>
                  <select value={reportFormat} onChange={(e) => setReportFormat(e.target.value as any)}>
                    <option value="pdf">PDF Document (.pdf)</option>
                    <option value="excel">Excel Workbook (.xlsx)</option>
                  </select>
                </div>
              </div>
            </div>
            <div className="card-footer">
              <button
                onClick={handleGenerateReport}
                className="btn-primary"
                disabled={isGeneratingReport}
              >
                <Download className="btn-icon" />
                {isGeneratingReport ? 'Generating Report...' : 'Generate & Download Report'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal: Add Collector Target */}
      {isAddTargetModalOpen && (
        <div className="modal-overlay">
          <div className="modal-card">
            <h3>Register Collector Target</h3>
            <form onSubmit={handleCreateTarget}>
              <div className="form-group">
                <label>Target Name</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Linux Production Server Cluster"
                  value={targetName}
                  onChange={(e) => setTargetName(e.target.value)}
                />
              </div>

              <div className="form-group">
                <label>Target Type</label>
                <select value={targetType} onChange={(e: any) => setTargetType(e.target.value)}>
                  <option value="ssh">SSH (Linux Host)</option>
                  <option value="winrm">WinRM / PowerShell (Windows)</option>
                  <option value="hyperv">Hyper-V Hypervisor</option>
                  <option value="docker">Docker Engine API (TLS)</option>
                </select>
              </div>

              <div className="form-group">
                <label>Host IP / Address / Endpoint</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. 192.168.1.100 or tcp://10.0.0.1:2376"
                  value={hostUrl}
                  onChange={(e) => setHostUrl(e.target.value)}
                />
              </div>

              <div className="form-group">
                <label>Port (Optional)</label>
                <input
                  type="number"
                  placeholder="e.g. 22 or 5986"
                  value={port}
                  onChange={(e) => setPort(e.target.value ? Number(e.target.value) : '')}
                />
              </div>

              <div className="form-group">
                <label>Credential Vault Reference (Secret Ref Key)</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. secret:ssh-dc1-key or secret:winrm-admin-pass"
                  value={credRef}
                  onChange={(e) => setCredRef(e.target.value)}
                />
                <small className="form-hint">Stored as encrypted secret reference. Plain text credentials are never displayed.</small>
              </div>

              <div className="modal-actions">
                <button type="button" onClick={() => setIsAddTargetModalOpen(false)} className="btn-secondary">
                  Cancel
                </button>
                <button type="submit" className="btn-primary" disabled={createTargetMutation.isPending}>
                  {createTargetMutation.isPending ? 'Saving...' : 'Register Target'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal: Create Data Center */}
      {isAddDcModalOpen && (
        <div className="modal-overlay">
          <div className="modal-card">
            <h3>Create Data Center Group</h3>
            <form onSubmit={handleCreateDC}>
              <div className="form-group">
                <label>Data Center Name</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Data Center Jakarta 1"
                  value={dcName}
                  onChange={(e) => setDcName(e.target.value)}
                />
              </div>

              <div className="form-group">
                <label>Location Code</label>
                <input
                  type="text"
                  placeholder="e.g. JKT-DC01"
                  value={dcLocation}
                  onChange={(e) => setDcLocation(e.target.value)}
                />
              </div>

              <div className="modal-actions">
                <button type="button" onClick={() => setIsAddDcModalOpen(false)} className="btn-secondary">
                  Cancel
                </button>
                <button type="submit" className="btn-primary" disabled={createDcMutation.isPending}>
                  {createDcMutation.isPending ? 'Creating...' : 'Create Data Center'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal: Assign Hosts to Data Center */}
      {assignDcId && (
        <div className="modal-overlay">
          <div className="modal-card modal-lg">
            <h3>Assign Host Nodes to Data Center</h3>
            <p>Select approved physical/hypervisor/docker host nodes to place in this Data Center root.</p>

            <div className="hosts-checklist">
              {!approvedHosts?.items || approvedHosts.items.length === 0 ? (
                <p className="empty-state">No approved host nodes available to assign.</p>
              ) : (
                approvedHosts.items
                  .filter((h) => h.type === 'physical_server' || h.type === 'hyperv_host' || h.type === 'docker_host')
                  .map((host) => (
                    <label key={host.id} className="checkbox-row">
                      <input
                        type="checkbox"
                        checked={selectedHostIds.includes(host.id)}
                        onChange={(e) => {
                          if (e.target.checked) {
                            setSelectedHostIds([...selectedHostIds, host.id]);
                          } else {
                            setSelectedHostIds(selectedHostIds.filter((id) => id !== host.id));
                          }
                        }}
                      />
                      <span>{host.name} ({host.type.replace('_', ' ')}) - {host.ip_address || 'No IP'}</span>
                    </label>
                  ))
              )}
            </div>

            <div className="modal-actions">
              <button onClick={() => setAssignDcId(null)} className="btn-secondary">
                Cancel
              </button>
              <button
                onClick={handleAssignHostsSubmit}
                className="btn-primary"
                disabled={assignHostsMutation.isPending || selectedHostIds.length === 0}
              >
                {assignHostsMutation.isPending ? 'Assigning...' : 'Assign Selected Hosts'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
