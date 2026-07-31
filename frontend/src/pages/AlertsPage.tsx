import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../services/apiClient';
import { AlertItem, AlertRuleItem } from '../types/api';
import { useAuth } from '../context/AuthContext';
import {
  Bell,
  AlertTriangle,
  ShieldAlert,
  CheckCircle2,
  Clock,
  Plus,
  RefreshCw,
  Check,
} from 'lucide-react';

export const AlertsPage: React.FC = () => {
  const { isAdmin } = useAuth();
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState<'active' | 'history' | 'rules'>('active');

  // ACK Modal State
  const [ackAlert, setAckAlert] = useState<AlertItem | null>(null);
  const [ackNote, setAckNote] = useState('');

  // Rule Creation Modal State
  const [isAddRuleOpen, setIsAddRuleOpen] = useState(false);
  const [metricName, setMetricName] = useState('cpu_usage');
  const [warnThresh, setWarnThresh] = useState<number | ''>(85);
  const [critThresh, setCritThresh] = useState<number | ''>(95);

  // Fetch Active Firing Alerts
  const { data: activeAlerts, isLoading: isLoadingActive, refetch: refetchActive } = useQuery<AlertItem[]>({
    queryKey: ['alerts', 'active'],
    queryFn: () => apiClient.get<AlertItem[]>('/alerts/active'),
  });

  // Fetch Alert History Log
  const { data: alertHistory, isLoading: isLoadingHistory } = useQuery<AlertItem[]>({
    queryKey: ['alerts', 'history'],
    queryFn: () => apiClient.get<AlertItem[]>('/alerts/history?limit=100'),
    enabled: activeTab === 'history',
  });

  // Fetch Alert Rules
  const { data: alertRules, isLoading: isLoadingRules } = useQuery<AlertRuleItem[]>({
    queryKey: ['alerts', 'rules'],
    queryFn: () => apiClient.get<AlertRuleItem[]>('/alerts/rules'),
    enabled: activeTab === 'rules',
  });

  // Acknowledge Alert Mutation
  const ackMutation = useMutation({
    mutationFn: ({ id, note }: { id: string; note: string }) =>
      apiClient.post<AlertItem>(`/alerts/${id}/acknowledge`, { note }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['alerts'] });
      setAckAlert(null);
      setAckNote('');
    },
  });

  // Create Rule Mutation
  const createRuleMutation = useMutation({
    mutationFn: (body: any) => apiClient.post<AlertRuleItem>('/alerts/rules', body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['alerts', 'rules'] });
      setIsAddRuleOpen(false);
    },
  });

  const handleConfirmAck = () => {
    if (!ackAlert) return;
    ackMutation.mutate({ id: ackAlert.id, note: ackNote });
  };

  const handleCreateRule = (e: React.FormEvent) => {
    e.preventDefault();
    createRuleMutation.mutate({
      metric_name: metricName,
      warning_threshold: warnThresh ? Number(warnThresh) : null,
      critical_threshold: critThresh ? Number(critThresh) : null,
      duration_seconds: 300,
    });
  };

  return (
    <div className="page-container">
      <header className="page-header">
        <div>
          <h1 className="page-title">Alert Management Engine</h1>
          <p className="page-subtitle">Real-time alert threshold evaluation, 15m deduplication &amp; escalation</p>
        </div>
        <button onClick={() => refetchActive()} className="btn-secondary">
          <RefreshCw className="btn-icon" /> Refresh
        </button>
      </header>

      {/* Tabs */}
      <div className="admin-tabs">
        <button
          className={`tab-btn ${activeTab === 'active' ? 'active' : ''}`}
          onClick={() => setActiveTab('active')}
        >
          <Bell className="tab-icon" /> Active Firing Alerts ({activeAlerts?.length || 0})
        </button>

        <button
          className={`tab-btn ${activeTab === 'history' ? 'active' : ''}`}
          onClick={() => setActiveTab('history')}
        >
          <Clock className="tab-icon" /> Historical Alert Logs
        </button>

        <button
          className={`tab-btn ${activeTab === 'rules' ? 'active' : ''}`}
          onClick={() => setActiveTab('rules')}
        >
          <ShieldAlert className="tab-icon" /> Threshold Rules
        </button>
      </div>

      {/* Tab 1: Firing Active Alerts */}
      {activeTab === 'active' && (
        <div className="tab-content">
          {isLoadingActive ? (
            <div className="loading-state">Evaluating active alerts...</div>
          ) : !activeAlerts || activeAlerts.length === 0 ? (
            <div className="empty-state-success">
              <CheckCircle2 className="success-icon" />
              <p>No firing alerts detected. All systems operating within normal parameters.</p>
            </div>
          ) : (
            <div className="cards-grid">
              {activeAlerts.map((alert) => (
                <div key={alert.id} className={`target-card alert-card ${alert.severity}`}>
                  <div className="card-header">
                    <div className="alert-title-box">
                      {alert.severity === 'critical' ? (
                        <ShieldAlert className="alert-card-icon critical" />
                      ) : (
                        <AlertTriangle className="alert-card-icon warning" />
                      )}
                      <h4>{alert.severity.toUpperCase()} ALERT</h4>
                    </div>
                    {alert.escalated && <span className="escalated-tag">ESCALATED (&gt;15m)</span>}
                  </div>
                  <div className="card-body">
                    <p className="alert-msg">{alert.message}</p>
                    <div className="info-row">
                      <span className="label">Triggered At:</span>
                      <span className="val">{new Date(alert.triggered_at).toLocaleString()}</span>
                    </div>
                  </div>
                  <div className="card-footer">
                    <button
                      onClick={() => setAckAlert(alert)}
                      className="btn-primary btn-block"
                    >
                      <Check className="btn-icon" /> Acknowledge Alert
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Tab 2: Alert History */}
      {activeTab === 'history' && (
        <div className="tab-content">
          {isLoadingHistory ? (
            <div className="loading-state">Loading historical alerts...</div>
          ) : !alertHistory || alertHistory.length === 0 ? (
            <div className="empty-state">No historical alert logs recorded.</div>
          ) : (
            <div className="table-container">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Severity</th>
                    <th>Status</th>
                    <th>Message</th>
                    <th>Triggered At</th>
                    <th>Resolved At</th>
                    <th>Acknowledged By</th>
                  </tr>
                </thead>
                <tbody>
                  {alertHistory.map((alert) => (
                    <tr key={alert.id}>
                      <td>
                        <span className={`badge badge-${alert.severity === 'critical' ? 'down' : 'warning'}`}>
                          {alert.severity.toUpperCase()}
                        </span>
                      </td>
                      <td>
                        <span className={`review-tag ${alert.status}`}>
                          {alert.status}
                        </span>
                      </td>
                      <td>{alert.message}</td>
                      <td>{new Date(alert.triggered_at).toLocaleString()}</td>
                      <td>{alert.resolved_at ? new Date(alert.resolved_at).toLocaleString() : '-'}</td>
                      <td>{alert.acknowledged_by || '-'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Tab 3: Alert Rules */}
      {activeTab === 'rules' && (
        <div className="tab-content">
          <div className="tab-header">
            <h3>Threshold Configuration Rules</h3>
            {isAdmin && (
              <button onClick={() => setIsAddRuleOpen(true)} className="btn-primary">
                <Plus className="btn-icon" /> Add Alert Rule
              </button>
            )}
          </div>

          {isLoadingRules ? (
            <div className="loading-state">Loading alert rules...</div>
          ) : !alertRules || alertRules.length === 0 ? (
            <div className="empty-state">No custom alert rules configured. Using default system thresholds.</div>
          ) : (
            <div className="table-container">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Metric</th>
                    <th>Warning Threshold</th>
                    <th>Critical Threshold</th>
                    <th>Duration Policy</th>
                    <th>Enabled</th>
                  </tr>
                </thead>
                <tbody>
                  {alertRules.map((rule) => (
                    <tr key={rule.id}>
                      <td><code>{rule.metric_name}</code></td>
                      <td>{rule.warning_threshold ? `> ${rule.warning_threshold}%` : 'N/A'}</td>
                      <td>{rule.critical_threshold ? `> ${rule.critical_threshold}%` : 'N/A'}</td>
                      <td>{Math.round(rule.duration_seconds / 60)} minutes</td>
                      <td>{rule.is_enabled ? 'Yes' : 'No'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Modal: ACK Alert */}
      {ackAlert && (
        <div className="modal-overlay">
          <div className="modal-card">
            <h3>Acknowledge Alert</h3>
            <p>Acknowledge firing alert: <strong>{ackAlert.message}</strong></p>
            <div className="form-group">
              <label>Operator Audit Note</label>
              <textarea
                rows={3}
                className="input-textarea"
                placeholder="Enter investigation details or remediation steps..."
                value={ackNote}
                onChange={(e) => setAckNote(e.target.value)}
              />
            </div>
            <div className="modal-actions">
              <button onClick={() => setAckAlert(null)} className="btn-secondary">
                Cancel
              </button>
              <button onClick={handleConfirmAck} className="btn-primary" disabled={ackMutation.isPending}>
                {ackMutation.isPending ? 'Submitting...' : 'Confirm Acknowledgement'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal: Create Alert Rule */}
      {isAddRuleOpen && (
        <div className="modal-overlay">
          <div className="modal-card">
            <h3>Create Custom Alert Threshold Rule</h3>
            <form onSubmit={handleCreateRule}>
              <div className="form-group">
                <label>Metric Name</label>
                <select value={metricName} onChange={(e) => setMetricName(e.target.value)}>
                  <option value="cpu_usage">CPU Usage Ratio</option>
                  <option value="ram_usage">RAM Usage Bytes</option>
                  <option value="disk_usage">Disk Usage Bytes</option>
                </select>
              </div>

              <div className="form-group">
                <label>Warning Threshold (%)</label>
                <input
                  type="number"
                  value={warnThresh}
                  onChange={(e) => setWarnThresh(e.target.value ? Number(e.target.value) : '')}
                />
              </div>

              <div className="form-group">
                <label>Critical Threshold (%)</label>
                <input
                  type="number"
                  value={critThresh}
                  onChange={(e) => setCritThresh(e.target.value ? Number(e.target.value) : '')}
                />
              </div>

              <div className="modal-actions">
                <button type="button" onClick={() => setIsAddRuleOpen(false)} className="btn-secondary">
                  Cancel
                </button>
                <button type="submit" className="btn-primary" disabled={createRuleMutation.isPending}>
                  {createRuleMutation.isPending ? 'Saving...' : 'Create Rule'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
