import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../services/apiClient';
import { CollectorTarget, DataCenter, PaginatedNodes, QuarterlyAuditReviewItem, ReportScheduleItem, UserDetailItem } from '../types/api';
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
  ShieldCheck,
  UserCheck,
  UserX,
  Award,
  Calendar,
  Mail,
  Play,
  Trash2,
  Users,
  Key,
} from 'lucide-react';

export const AdministrationPage: React.FC = () => {
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState<'collectors' | 'datacenters' | 'pending' | 'reports' | 'governance' | 'users'>('collectors');
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

  // Governance State
  const [isCreateCampaignOpen, setIsCreateCampaignOpen] = useState(false);
  const [govQuarter, setGovQuarter] = useState('2026-Q3');
  const [govTitle, setGovTitle] = useState('2026 Q3 RBAC Access & Governance Review');
  const [govReviewer, setGovReviewer] = useState('admin');
  const [signoffCampaignId, setSignoffCampaignId] = useState<string | null>(null);
  const [signoffComment, setSignoffComment] = useState('');
  const [selectedCampaignId, setSelectedCampaignId] = useState<string | null>(null);

  // Report Schedule State
  const [isCreateScheduleOpen, setIsCreateScheduleOpen] = useState(false);
  const [schedName, setSchedName] = useState('Weekly Executive Uptime Report');
  const [schedFreq, setSchedFreq] = useState<'daily' | 'weekly' | 'monthly'>('weekly');
  const [schedReportType, setSchedReportType] = useState<'weekly' | 'monthly'>('weekly');
  const [schedFormat, setSchedFormat] = useState<'pdf' | 'excel' | 'both'>('pdf');
  const [schedRecipients, setSchedRecipients] = useState('exec@company.com, ops@company.com');

  // User Management & RBAC State
  const [isCreateUserOpen, setIsCreateUserOpen] = useState(false);
  const [newUsername, setNewUsername] = useState('');
  const [newEmail, setNewEmail] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [newRole, setNewRole] = useState<'admin' | 'operator' | 'viewer'>('operator');
  const [selectedPerms, setSelectedPerms] = useState<string[]>(['nodes:read', 'nodes:write', 'topology:read']);
  const [scopesStr, setScopesStr] = useState('Jakarta-DC, *');

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

  // Fetch Governance Audit Reviews
  const { data: auditReviews, isLoading: isLoadingGov } = useQuery<QuarterlyAuditReviewItem[]>({
    queryKey: ['governance-reviews'],
    queryFn: () => apiClient.get<QuarterlyAuditReviewItem[]>('/governance/reviews'),
    enabled: activeTab === 'governance',
  });

  // Fetch Single Governance Audit Campaign Details
  const { data: selectedCampaign } = useQuery<QuarterlyAuditReviewItem>({
    queryKey: ['governance-review', selectedCampaignId],
    queryFn: () => apiClient.get<QuarterlyAuditReviewItem>(`/governance/reviews/${selectedCampaignId}`),
    enabled: !!selectedCampaignId,
  });

  // Fetch Report Schedules
  const { data: reportSchedules, isLoading: isLoadingSchedules } = useQuery<ReportScheduleItem[]>({
    queryKey: ['report-schedules'],
    queryFn: () => apiClient.get<ReportScheduleItem[]>('/reports/schedules'),
    enabled: activeTab === 'reports',
  });

  // Fetch Users List
  const { data: userList, isLoading: isLoadingUsers } = useQuery<UserDetailItem[]>({
    queryKey: ['users-list'],
    queryFn: () => apiClient.get<UserDetailItem[]>('/users'),
    enabled: activeTab === 'users',
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
      queryClient.invalidateQueries({ queryKey: ['datacenters'] });
      setAssignDcId(null);
      setSelectedHostIds([]);
    },
  });

  // Approve Node Mutation
  const approveNodeMutation = useMutation({
    mutationFn: (nodeId: string) => apiClient.post(`/nodes/${nodeId}/approve`, {}),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['nodes', 'pending-queue'] });
    },
  });

  // Reject Node Mutation
  const rejectNodeMutation = useMutation({
    mutationFn: (nodeId: string) => apiClient.post(`/nodes/${nodeId}/reject`, {}),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['nodes', 'pending-queue'] });
    },
  });

  // Create Governance Campaign Mutation
  const createGovCampaignMutation = useMutation({
    mutationFn: (body: any) => apiClient.post<QuarterlyAuditReviewItem>('/governance/reviews', body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['governance-reviews'] });
      setIsCreateCampaignOpen(false);
    },
  });

  // Review Decision Mutation
  const reviewDecisionMutation = useMutation({
    mutationFn: ({ reviewId, userId, decision }: { reviewId: string; userId: string; decision: string }) =>
      apiClient.post(`/governance/reviews/${reviewId}/decisions`, { user_id: userId, decision }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['governance-review', selectedCampaignId] });
      queryClient.invalidateQueries({ queryKey: ['governance-reviews'] });
    },
  });

  // Executive Sign-off Mutation
  const signoffMutation = useMutation({
    mutationFn: ({ reviewId, comments }: { reviewId: string; comments: string }) =>
      apiClient.post(`/governance/reviews/${reviewId}/sign-off`, { comments }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['governance-reviews'] });
      queryClient.invalidateQueries({ queryKey: ['governance-review', selectedCampaignId] });
      setSignoffCampaignId(null);
      setSignoffComment('');
    },
  });

  // Create Report Schedule Mutation
  const createScheduleMutation = useMutation({
    mutationFn: (body: any) => apiClient.post<ReportScheduleItem>('/reports/schedules', body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['report-schedules'] });
      setIsCreateScheduleOpen(false);
    },
  });

  // Trigger Report Schedule Mutation
  const triggerScheduleMutation = useMutation({
    mutationFn: (scheduleId: string) => apiClient.post<ReportScheduleItem>(`/reports/schedules/${scheduleId}/trigger`, {}),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['report-schedules'] });
    },
  });

  // Delete Report Schedule Mutation
  const deleteScheduleMutation = useMutation({
    mutationFn: (scheduleId: string) => apiClient.delete(`/reports/schedules/${scheduleId}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['report-schedules'] });
    },
  });

  // Create User Mutation
  const createUserMutation = useMutation({
    mutationFn: (body: any) => apiClient.post<UserDetailItem>('/users', body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users-list'] });
      setIsCreateUserOpen(false);
      setNewUsername('');
      setNewEmail('');
      setNewPassword('');
    },
  });

  // Delete User Mutation
  const deleteUserMutation = useMutation({
    mutationFn: (userId: string) => apiClient.delete(`/users/${userId}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users-list'] });
    },
  });

  const resetTargetForm = () => {
    setTargetName('');
    setTargetType('ssh');
    setHostUrl('');
    setPort('');
    setCredRef('');
  };

  const handleCreateTargetSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    createTargetMutation.mutate({
      name: targetName,
      target_type: targetType,
      host_or_url: hostUrl,
      port: port ? Number(port) : null,
      credential_reference: credRef || 'default_key',
      poll_interval_seconds: 60,
    });
  };

  const handleCreateDcSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    createDcMutation.mutate({
      name: dcName,
      location: dcLocation || undefined,
    });
  };

  const handleAssignHostsSubmit = () => {
    if (!assignDcId || selectedHostIds.length === 0) return;
    assignHostsMutation.mutate({ dcId: assignDcId, hostIds: selectedHostIds });
  };

  const handleCreateGovCampaignSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    createGovCampaignMutation.mutate({
      quarter: govQuarter,
      title: govTitle,
      reviewer_username: govReviewer,
      duration_days: 14,
    });
  };

  const handleCreateScheduleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const emailsList = schedRecipients
      .split(',')
      .map((s) => s.trim())
      .filter((s) => s.length > 0);

    createScheduleMutation.mutate({
      name: schedName,
      frequency: schedFreq,
      report_type: schedReportType,
      export_format: schedFormat,
      recipients: emailsList,
      is_enabled: true,
    });
  };

  const handleCreateUserSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const scopesList = scopesStr
      .split(',')
      .map((s) => s.trim())
      .filter((s) => s.length > 0);

    createUserMutation.mutate({
      username: newUsername,
      email: newEmail,
      password: newPassword,
      role: newRole,
      custom_permissions: selectedPerms,
      allowed_group_scopes: scopesList,
      is_active: true,
    });
  };

  const handleDownloadReport = async () => {
    setIsGeneratingReport(true);
    try {
      const endpoint = reportFormat === 'pdf' ? '/reports/download/pdf' : '/reports/download/excel';
      const response = await apiClient.get<Blob>(`${endpoint}?report_type=${reportType}`, {
        responseType: 'blob',
      });
      const url = window.URL.createObjectURL(new Blob([response]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `Infrastructure_Report_${reportType}_${Date.now()}.${reportFormat === 'pdf' ? 'pdf' : 'xlsx'}`);
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch (err) {
      console.error('Report download failed:', err);
    } finally {
      setIsGeneratingReport(false);
    }
  };

  const availablePermList = [
    { key: 'nodes:read', label: 'Read Nodes' },
    { key: 'nodes:write', label: 'Manage Nodes' },
    { key: 'topology:read', label: 'Read Topology' },
    { key: 'topology:edit', label: 'Edit Topology' },
    { key: 'alerts:read', label: 'Read Alerts' },
    { key: 'alerts:ack', label: 'Acknowledge Alerts' },
    { key: 'reports:export', label: 'Export Reports' },
    { key: 'vault:manage', label: 'Manage Secrets' },
  ];

  return (
    <div className="page-container">
      <header className="page-header">
        <div>
          <h1 className="page-title">System Administration &amp; Governance</h1>
          <p className="page-subtitle">Manage collectors, data centers, node approvals, reports, RBAC users &amp; quarterly audit reviews</p>
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
          <ShieldAlert className="tab-icon" /> Pending Approvals ({pendingNodes?.total || 0})
        </button>

        <button
          className={`tab-btn ${activeTab === 'reports' ? 'active' : ''}`}
          onClick={() => setActiveTab('reports')}
        >
          <FileText className="tab-icon" /> Executive Reports
        </button>

        <button
          className={`tab-btn ${activeTab === 'users' ? 'active' : ''}`}
          onClick={() => setActiveTab('users')}
        >
          <Users className="tab-icon" /> User Management &amp; RBAC
        </button>

        <button
          className={`tab-btn ${activeTab === 'governance' ? 'active' : ''}`}
          onClick={() => setActiveTab('governance')}
        >
          <ShieldCheck className="tab-icon" /> Governance &amp; Audit
        </button>
      </div>

      {/* Tab 1: Collector Targets */}
      {activeTab === 'collectors' && (
        <div className="tab-content">
          <div className="tab-header">
            <h3>Infrastructure Collector Targets</h3>
            <button onClick={() => setIsAddTargetModalOpen(true)} className="btn-primary">
              <Plus className="btn-icon" /> Add Collector Target
            </button>
          </div>

          {isLoadingTargets ? (
            <div className="loading-state">Loading collector targets...</div>
          ) : !targets || targets.length === 0 ? (
            <div className="empty-state">No collector targets configured yet.</div>
          ) : (
            <div className="cards-grid">
              {targets.map((target) => (
                <div key={target.id} className="target-card">
                  <div className="card-header">
                    <h4>{target.name}</h4>
                    <span className={`type-badge ${target.target_type}`}>{target.target_type.toUpperCase()}</span>
                  </div>
                  <div className="card-body">
                    <p><strong>Host/URL:</strong> {target.host_or_url}</p>
                    {target.port && <p><strong>Port:</strong> {target.port}</p>}
                    <p><strong>Poll Interval:</strong> {target.poll_interval_seconds}s</p>
                    <p><strong>Status:</strong> {target.is_enabled ? 'Enabled' : 'Disabled'}</p>

                    {testResult && testResult.id === target.id && (
                      <div className={`test-feedback ${testResult.status}`}>
                        {testResult.status === 'success' ? <CheckCircle2 className="icon-success" /> : <AlertCircle className="icon-error" />}
                        <span>{testResult.message}</span>
                      </div>
                    )}
                  </div>
                  <div className="card-footer">
                    <button
                      onClick={() => testConnectionMutation.mutate(target.id)}
                      className="btn-secondary btn-sm"
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
              <Plus className="btn-icon" /> Add Data Center
            </button>
          </div>

          {isLoadingDCs ? (
            <div className="loading-state">Loading data centers...</div>
          ) : !dataCenters || dataCenters.length === 0 ? (
            <div className="empty-state">No Data Centers configured.</div>
          ) : (
            <div className="cards-grid">
              {dataCenters.map((dc) => (
                <div key={dc.id} className="target-card dc-card">
                  <div className="card-header">
                    <h4>{dc.name}</h4>
                    <span className="type-badge dc">DATA CENTER</span>
                  </div>
                  <div className="card-body">
                    <p><strong>Location Code:</strong> {dc.metadata?.location || 'N/A'}</p>
                    <p><strong>Status:</strong> {dc.status.toUpperCase()}</p>
                  </div>
                  <div className="card-footer">
                    <button
                      onClick={() => {
                        setAssignDcId(dc.id);
                        setSelectedHostIds([]);
                      }}
                      className="btn-secondary btn-sm"
                    >
                      <Building2 className="btn-icon" /> Assign Host Nodes
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Tab 3: Pending Approvals Queue */}
      {activeTab === 'pending' && (
        <div className="tab-content">
          <div className="tab-header">
            <h3>Discovered Nodes Pending Approval</h3>
          </div>

          {!pendingNodes || pendingNodes.items.length === 0 ? (
            <div className="empty-state-success">
              <CheckCircle2 className="success-icon" />
              <p>All discovered nodes have been reviewed. No pending nodes in queue.</p>
            </div>
          ) : (
            <div className="table-container">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Node Name</th>
                    <th>Type</th>
                    <th>IP Address</th>
                    <th>OS</th>
                    <th>Discovered At</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {pendingNodes.items.map((node) => (
                    <tr key={node.id}>
                      <td><strong>{node.name}</strong></td>
                      <td><span className="node-type-tag">{node.type.replace('_', ' ')}</span></td>
                      <td>{node.ip_address || '-'}</td>
                      <td>{node.os || '-'}</td>
                      <td>{new Date(node.created_at).toLocaleString()}</td>
                      <td>
                        <div className="action-buttons">
                          <button
                            onClick={() => approveNodeMutation.mutate(node.id)}
                            className="btn-success btn-sm"
                            disabled={approveNodeMutation.isPending}
                          >
                            <Check className="btn-icon" /> Approve
                          </button>
                          <button
                            onClick={() => rejectNodeMutation.mutate(node.id)}
                            className="btn-danger btn-sm"
                            disabled={rejectNodeMutation.isPending}
                          >
                            Reject
                          </button>
                        </div>
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
            <h3>Executive Recapitulation Reports</h3>
          </div>

          <div className="report-generator-card">
            <p className="report-desc">Generate aggregated system uptime, incident log, and asset inventory reports for executive stakeholders.</p>
            <div className="report-controls">
              <div className="form-group">
                <label>Report Period</label>
                <select value={reportType} onChange={(e) => setReportType(e.target.value as any)}>
                  <option value="weekly">Weekly Summary Report</option>
                  <option value="monthly">Monthly Full Executive Audit</option>
                </select>
              </div>

              <div className="form-group">
                <label>Export Format</label>
                <select value={reportFormat} onChange={(e) => setReportFormat(e.target.value as any)}>
                  <option value="pdf">PDF Document (.pdf)</option>
                  <option value="excel">Excel Workbook (.xlsx)</option>
                </select>
              </div>
            </div>

            <button onClick={handleDownloadReport} className="btn-primary" disabled={isGeneratingReport}>
              <Download className="btn-icon" /> {isGeneratingReport ? 'Generating Report...' : `Download ${reportFormat.toUpperCase()} Report`}
            </button>
          </div>

          {/* Section: Automated Report Delivery Schedules */}
          <div className="tab-header" style={{ marginTop: '32px' }}>
            <h3>Automated Report Delivery Schedules (Cron Engine)</h3>
            <button onClick={() => setIsCreateScheduleOpen(true)} className="btn-primary">
              <Plus className="btn-icon" /> Create Schedule Rule
            </button>
          </div>

          {isLoadingSchedules ? (
            <div className="loading-state">Loading automated report schedules...</div>
          ) : !reportSchedules || reportSchedules.length === 0 ? (
            <div className="empty-state">No automated report schedules configured yet.</div>
          ) : (
            <div className="table-container">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Schedule Name</th>
                    <th>Frequency</th>
                    <th>Format</th>
                    <th>Recipients</th>
                    <th>Last Run</th>
                    <th>Next Run</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {reportSchedules.map((sched) => (
                    <tr key={sched.id}>
                      <td><strong>{sched.name}</strong></td>
                      <td><span className="badge badge-info">{sched.frequency.toUpperCase()}</span></td>
                      <td><code>{sched.export_format.toUpperCase()}</code></td>
                      <td>
                        <span style={{ fontSize: '0.85rem' }}>
                          <Mail size={12} className="btn-icon" /> {sched.recipients.join(', ')}
                        </span>
                      </td>
                      <td>{sched.last_run_at ? new Date(sched.last_run_at).toLocaleString() : 'Never'}</td>
                      <td>{sched.next_run_at ? new Date(sched.next_run_at).toLocaleString() : 'Pending'}</td>
                      <td>
                        <div className="action-buttons">
                          <button
                            onClick={() => triggerScheduleMutation.mutate(sched.id)}
                            className="btn-success btn-sm"
                            disabled={triggerScheduleMutation.isPending}
                            title="Run Schedule Now"
                          >
                            <Play size={12} /> Trigger Now
                          </button>
                          <button
                            onClick={() => deleteScheduleMutation.mutate(sched.id)}
                            className="btn-danger btn-sm"
                            disabled={deleteScheduleMutation.isPending}
                            title="Delete Schedule"
                          >
                            <Trash2 size={12} />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Tab 5: User Management & Granular RBAC */}
      {activeTab === 'users' && (
        <div className="tab-content">
          <div className="tab-header">
            <h3>User Accounts &amp; Granular RBAC Management</h3>
            <button onClick={() => setIsCreateUserOpen(true)} className="btn-primary">
              <Plus className="btn-icon" /> Create User Account
            </button>
          </div>

          {isLoadingUsers ? (
            <div className="loading-state">Loading user accounts...</div>
          ) : !userList || userList.length === 0 ? (
            <div className="empty-state">No users found.</div>
          ) : (
            <div className="table-container">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Username</th>
                    <th>Email</th>
                    <th>System Role</th>
                    <th>Granular Permissions</th>
                    <th>Node Scopes</th>
                    <th>Status</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {userList.map((user) => {
                    const perms = user.custom_permissions?.permissions || [];
                    const scopes = user.allowed_group_scopes?.scopes || ['*'];
                    return (
                      <tr key={user.id}>
                        <td><strong>{user.username}</strong></td>
                        <td>{user.email}</td>
                        <td>
                          <span className={`badge badge-${user.role === 'admin' ? 'up' : user.role === 'operator' ? 'warning' : 'info'}`}>
                            {user.role.toUpperCase()}
                          </span>
                        </td>
                        <td>
                          <div style={{ display: 'flex', gap: '4px', flexWrap: 'wrap' }}>
                            {perms.length === 0 ? (
                              <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Default Role</span>
                            ) : (
                              perms.map((p) => (
                                <code key={p} className="node-type-tag" style={{ fontSize: '0.75rem' }}>{p}</code>
                              ))
                            )}
                          </div>
                        </td>
                        <td>
                          <div style={{ display: 'flex', gap: '4px', flexWrap: 'wrap' }}>
                            {scopes.map((s) => (
                              <span key={s} className="badge badge-subtle" style={{ fontSize: '0.75rem' }}>{s}</span>
                            ))}
                          </div>
                        </td>
                        <td>
                          <span className={`status-pill ${user.is_active ? 'online' : 'offline'}`}>
                            {user.is_active ? 'ACTIVE' : 'INACTIVE'}
                          </span>
                        </td>
                        <td>
                          <div className="action-buttons">
                            <button
                              onClick={() => deleteUserMutation.mutate(user.id)}
                              className="btn-danger btn-sm"
                              disabled={deleteUserMutation.isPending || user.username === 'admin'}
                              title="Delete User"
                            >
                              <Trash2 size={12} />
                            </button>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Tab 6: Governance & Quarterly Audit */}
      {activeTab === 'governance' && (
        <div className="tab-content">
          <div className="tab-header">
            <h3>Quarterly RBAC Access Audit Reviews</h3>
            <button onClick={() => setIsCreateCampaignOpen(true)} className="btn-primary">
              <Plus className="btn-icon" /> Create Audit Campaign
            </button>
          </div>

          {isLoadingGov ? (
            <div className="loading-state">Loading governance audit reviews...</div>
          ) : !auditReviews || auditReviews.length === 0 ? (
            <div className="empty-state">No governance audit reviews found.</div>
          ) : (
            <div className="cards-grid">
              {auditReviews.map((rev) => {
                const total = Object.keys(rev.user_snapshots || {}).length;
                const done = Object.keys(rev.review_decisions || {}).length;
                const pct = total > 0 ? Math.round((done / total) * 100) : 100;

                return (
                  <div key={rev.id} className="target-card">
                    <div className="card-header">
                      <h4>{rev.title}</h4>
                      <span className={`type-badge ${rev.status === 'APPROVED' ? 'active' : rev.status === 'OVERDUE_ESCALATED' ? 'critical' : 'warning'}`}>
                        {rev.status}
                      </span>
                    </div>
                    <div className="card-body">
                      <p><strong>Quarter:</strong> <code>{rev.quarter}</code></p>
                      <p><strong>Reviewer:</strong> {rev.reviewer_username}</p>
                      <p><strong>Due Date:</strong> {new Date(rev.due_date).toLocaleDateString()}</p>
                      <p><strong>Progress:</strong> {done} / {total} accounts reviewed ({pct}%)</p>

                      {rev.signoff_by && (
                        <div style={{ marginTop: '8px', padding: '6px', background: 'var(--bg-subtle)', borderRadius: '4px', fontSize: '0.8rem' }}>
                          <Award size={12} className="icon-blue" /> Signed off by <strong>{rev.signoff_by}</strong> on {new Date(rev.signoff_at!).toLocaleDateString()}
                        </div>
                      )}
                    </div>
                    <div className="card-footer" style={{ gap: '8px' }}>
                      <button
                        onClick={() => setSelectedCampaignId(rev.id)}
                        className="btn-secondary btn-sm"
                      >
                        <ShieldCheck size={14} /> View / Review Accounts
                      </button>
                      {rev.status !== 'APPROVED' && (
                        <button
                          onClick={() => setSignoffCampaignId(rev.id)}
                          className="btn-success btn-sm"
                        >
                          <Check size={14} /> Executive Sign-off
                        </button>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          {/* Detailed User Account Review Drawer/Modal */}
          {selectedCampaign && (
            <div className="modal-overlay">
              <div className="modal-card modal-lg">
                <h3>{selectedCampaign.title} (Snapshot Review)</h3>
                <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                  Quarter: <code>{selectedCampaign.quarter}</code> | Reviewer: {selectedCampaign.reviewer_username}
                </p>

                <div className="table-container" style={{ maxHeight: '360px', overflowY: 'auto' }}>
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>User Account</th>
                        <th>Email</th>
                        <th>Assigned Role</th>
                        <th>Decision</th>
                        <th>Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {Object.values(selectedCampaign.user_snapshots || {}).map((u: any) => {
                        const dec = selectedCampaign.review_decisions?.[u.user_id];
                        return (
                          <tr key={u.user_id}>
                            <td><strong>{u.username}</strong></td>
                            <td>{u.email}</td>
                            <td><code className="node-type-tag">{u.role}</code></td>
                            <td>
                              {dec ? (
                                <span className={`badge badge-${dec.decision === 'approve' ? 'up' : dec.decision === 'revoke' ? 'down' : 'warning'}`}>
                                  {dec.decision.toUpperCase()}
                                </span>
                              ) : (
                                <span className="review-tag pending">PENDING</span>
                              )}
                            </td>
                            <td>
                              <div className="action-buttons">
                                <button
                                  className="btn-success btn-sm"
                                  onClick={() => reviewDecisionMutation.mutate({ reviewId: selectedCampaign.id, userId: u.user_id, decision: 'approve' })}
                                  disabled={selectedCampaign.status === 'APPROVED'}
                                >
                                  <UserCheck size={12} /> Approve
                                </button>
                                <button
                                  className="btn-danger btn-sm"
                                  onClick={() => reviewDecisionMutation.mutate({ reviewId: selectedCampaign.id, userId: u.user_id, decision: 'revoke' })}
                                  disabled={selectedCampaign.status === 'APPROVED'}
                                >
                                  <UserX size={12} /> Revoke
                                </button>
                              </div>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>

                <div className="modal-actions">
                  <button onClick={() => setSelectedCampaignId(null)} className="btn-secondary">
                    Close Review Drawer
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Modal: Create Collector Target */}
      {isAddTargetModalOpen && (
        <div className="modal-overlay">
          <div className="modal-card">
            <h3>Add Collector Target</h3>
            <form onSubmit={handleCreateTargetSubmit}>
              <div className="form-group">
                <label>Target Name</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Production Linux Cluster 01"
                  value={targetName}
                  onChange={(e) => setTargetName(e.target.value)}
                />
              </div>

              <div className="form-group">
                <label>Target Type</label>
                <select value={targetType} onChange={(e) => setTargetType(e.target.value as any)}>
                  <option value="ssh">SSH (Linux Server)</option>
                  <option value="winrm">WinRM (Windows Server)</option>
                  <option value="hyperv">Hyper-V Host</option>
                  <option value="docker">Docker Host / Swarm</option>
                </select>
              </div>

              <div className="form-group">
                <label>Host / IP Address / URL</label>
                <input
                  type="text"
                  required
                  placeholder="10.0.0.15 or https://docker.company.internal"
                  value={hostUrl}
                  onChange={(e) => setHostUrl(e.target.value)}
                />
              </div>

              <div className="form-group">
                <label>Port (Optional)</label>
                <input
                  type="number"
                  placeholder="22 for SSH, 5986 for WinRM"
                  value={port}
                  onChange={(e) => setPort(e.target.value ? Number(e.target.value) : '')}
                />
              </div>

              <div className="form-group">
                <label>Credential Key Reference</label>
                <input
                  type="text"
                  placeholder="e.g. prod_ssh_key_v1"
                  value={credRef}
                  onChange={(e) => setCredRef(e.target.value)}
                />
              </div>

              <div className="modal-actions">
                <button type="button" onClick={() => setIsAddTargetModalOpen(false)} className="btn-secondary">
                  Cancel
                </button>
                <button type="submit" className="btn-primary" disabled={createTargetMutation.isPending}>
                  {createTargetMutation.isPending ? 'Saving...' : 'Add Target'}
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
            <h3>Add New Data Center</h3>
            <form onSubmit={handleCreateDcSubmit}>
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

      {/* Modal: Create Governance Campaign */}
      {isCreateCampaignOpen && (
        <div className="modal-overlay">
          <div className="modal-card">
            <h3>Create Quarterly RBAC Audit Campaign</h3>
            <form onSubmit={handleCreateGovCampaignSubmit}>
              <div className="form-group">
                <label>Quarter Code</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. 2026-Q3"
                  value={govQuarter}
                  onChange={(e) => setGovQuarter(e.target.value)}
                />
              </div>

              <div className="form-group">
                <label>Campaign Title</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. 2026 Q3 Access & RBAC Audit"
                  value={govTitle}
                  onChange={(e) => setGovTitle(e.target.value)}
                />
              </div>

              <div className="form-group">
                <label>Assigned Reviewer Username</label>
                <input
                  type="text"
                  required
                  placeholder="admin"
                  value={govReviewer}
                  onChange={(e) => setGovReviewer(e.target.value)}
                />
              </div>

              <div className="modal-actions">
                <button type="button" onClick={() => setIsCreateCampaignOpen(false)} className="btn-secondary">
                  Cancel
                </button>
                <button type="submit" className="btn-primary" disabled={createGovCampaignMutation.isPending}>
                  {createGovCampaignMutation.isPending ? 'Creating...' : 'Launch Campaign'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal: Executive Sign-off */}
      {signoffCampaignId && (
        <div className="modal-overlay">
          <div className="modal-card">
            <h3>Executive Sign-off Audit Review</h3>
            <p>Formally approve and sign off on this quarterly governance review.</p>
            <div className="form-group">
              <label>Executive Sign-off Comments</label>
              <textarea
                rows={3}
                className="input-textarea"
                placeholder="Enter executive sign-off comments..."
                value={signoffComment}
                onChange={(e) => setSignoffComment(e.target.value)}
              />
            </div>
            <div className="modal-actions">
              <button onClick={() => setSignoffCampaignId(null)} className="btn-secondary">
                Cancel
              </button>
              <button
                onClick={() => signoffMutation.mutate({ reviewId: signoffCampaignId, comments: signoffComment })}
                className="btn-primary"
                disabled={signoffMutation.isPending}
              >
                {signoffMutation.isPending ? 'Signing Off...' : 'Confirm Executive Sign-off'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal: Create Automated Report Schedule */}
      {isCreateScheduleOpen && (
        <div className="modal-overlay">
          <div className="modal-card">
            <h3>Create Automated Report Delivery Schedule</h3>
            <form onSubmit={handleCreateScheduleSubmit}>
              <div className="form-group">
                <label>Schedule Name</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Weekly Executive Uptime Report"
                  value={schedName}
                  onChange={(e) => setSchedName(e.target.value)}
                />
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                <div className="form-group">
                  <label>Delivery Frequency</label>
                  <select value={schedFreq} onChange={(e) => setSchedFreq(e.target.value as any)}>
                    <option value="weekly">Weekly (Every 7 Days)</option>
                    <option value="monthly">Monthly (Every 30 Days)</option>
                    <option value="daily">Daily</option>
                  </select>
                </div>

                <div className="form-group">
                  <label>Export Format</label>
                  <select value={schedFormat} onChange={(e) => setSchedFormat(e.target.value as any)}>
                    <option value="pdf">PDF Attachment</option>
                    <option value="excel">Excel Attachment</option>
                    <option value="both">Both (PDF &amp; Excel)</option>
                  </select>
                </div>
              </div>

              <div className="form-group">
                <label>Recipient Email Addresses (Comma Separated)</label>
                <input
                  type="text"
                  required
                  placeholder="exec@company.com, ops@company.com"
                  value={schedRecipients}
                  onChange={(e) => setSchedRecipients(e.target.value)}
                />
              </div>

              <div className="modal-actions">
                <button type="button" onClick={() => setIsCreateScheduleOpen(false)} className="btn-secondary">
                  Cancel
                </button>
                <button type="submit" className="btn-primary" disabled={createScheduleMutation.isPending}>
                  {createScheduleMutation.isPending ? 'Creating...' : 'Save Schedule Rule'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal: Create User Account & Granular RBAC */}
      {isCreateUserOpen && (
        <div className="modal-overlay">
          <div className="modal-card modal-lg">
            <h3>Create User Account &amp; Granular Permissions</h3>
            <form onSubmit={handleCreateUserSubmit}>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                <div className="form-group">
                  <label>Username</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. operator_jkt"
                    value={newUsername}
                    onChange={(e) => setNewUsername(e.target.value)}
                  />
                </div>

                <div className="form-group">
                  <label>Email Address</label>
                  <input
                    type="email"
                    required
                    placeholder="e.g. operator@company.com"
                    value={newEmail}
                    onChange={(e) => setNewEmail(e.target.value)}
                  />
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                <div className="form-group">
                  <label>Password</label>
                  <input
                    type="password"
                    required
                    placeholder="••••••••••••"
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                  />
                </div>

                <div className="form-group">
                  <label>System Role</label>
                  <select value={newRole} onChange={(e) => setNewRole(e.target.value as any)}>
                    <option value="operator">Operator (Custom RBAC)</option>
                    <option value="admin">Administrator (Full Access)</option>
                    <option value="viewer">Viewer (Read-only)</option>
                  </select>
                </div>
              </div>

              <div className="form-group">
                <label>Granular Permissions (Custom RBAC)</label>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', marginTop: '6px' }}>
                  {availablePermList.map((perm) => (
                    <label key={perm.key} className="checkbox-row" style={{ fontSize: '0.85rem' }}>
                      <input
                        type="checkbox"
                        checked={selectedPerms.includes(perm.key)}
                        onChange={(e) => {
                          if (e.target.checked) {
                            setSelectedPerms([...selectedPerms, perm.key]);
                          } else {
                            setSelectedPerms(selectedPerms.filter((p) => p !== perm.key));
                          }
                        }}
                      />
                      <span><strong>{perm.label}</strong> (<code>{perm.key}</code>)</span>
                    </label>
                  ))}
                </div>
              </div>

              <div className="form-group">
                <label>Allowed Node Group Scopes (Comma Separated)</label>
                <input
                  type="text"
                  placeholder="e.g. Jakarta-DC, Bandung-DC or * for all"
                  value={scopesStr}
                  onChange={(e) => setScopesStr(e.target.value)}
                />
              </div>

              <div className="modal-actions">
                <button type="button" onClick={() => setIsCreateUserOpen(false)} className="btn-secondary">
                  Cancel
                </button>
                <button type="submit" className="btn-primary" disabled={createUserMutation.isPending}>
                  {createUserMutation.isPending ? 'Creating...' : 'Create Account'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
