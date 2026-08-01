import React, { useEffect, useState } from 'react';
import { CloudflareStatusSummary } from '../types/api';
import { apiClient } from '../services/apiClient';

export const CloudflareEdgeCard: React.FC = () => {
  const [statusSummary, setStatusSummary] = useState<CloudflareStatusSummary | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [syncing, setSyncing] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const fetchStatus = async () => {
    try {
      setLoading(true);
      const res = await apiClient.fetchCloudflareStatus();
      if (res && res.data) {
        setStatusSummary(res.data);
      }
      setError(null);
    } catch (err: any) {
      setError(err?.message || 'Failed to fetch Cloudflare status');
    } finally {
      setLoading(false);
    }
  };

  const handleSync = async () => {
    try {
      setSyncing(true);
      const res = await apiClient.syncCloudflareStatus();
      if (res && res.data) {
        setStatusSummary(res.data);
      }
    } catch (err: any) {
      setError(err?.message || 'Sync failed');
    } finally {
      setSyncing(false);
    }
  };

  useEffect(() => {
    fetchStatus();
  }, []);

  const getStatusText = (indicator?: string) => {
    switch (indicator) {
      case 'none':
        return 'All Systems Operational';
      case 'minor':
        return 'Degraded Performance';
      case 'major':
        return 'Partial Edge Outage';
      case 'critical':
        return 'Major Edge Outage';
      default:
        return 'Unknown Status';
    }
  };

  return (
    <div style={{ padding: '16px', background: 'var(--bg-card)', border: '1px solid var(--border-color)', borderRadius: '12px', marginBottom: '20px' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div style={{ width: '38px', height: '38px', borderRadius: '8px', background: 'rgba(249, 115, 22, 0.15)', border: '1px solid rgba(249, 115, 22, 0.3)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#f97316', fontWeight: 'bold', fontSize: '1rem' }}>
            CF
          </div>
          <div>
            <h3 style={{ margin: 0, fontSize: '0.95rem', fontWeight: 600, color: 'var(--text-main)', display: 'flex', alignItems: 'center', gap: '8px' }}>
              Cloudflare Edge Status
            </h3>
            <p style={{ margin: 0, fontSize: '0.78rem', color: 'var(--text-muted)' }}>Global CDN, WAF &amp; Anycast Network Probe</p>
          </div>
        </div>
        <button
          onClick={handleSync}
          disabled={syncing}
          className="btn-secondary btn-sm"
          style={{ fontSize: '0.8rem', padding: '6px 12px' }}
        >
          {syncing ? 'Syncing...' : 'Sync Now'}
        </button>
      </div>

      {loading ? (
        <div style={{ padding: '16px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
          Probing Cloudflare Edge Status...
        </div>
      ) : error ? (
        <div className="test-feedback error" style={{ padding: '8px 12px' }}>
          <span>{error}</span>
        </div>
      ) : statusSummary ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '10px 14px', background: 'var(--bg-subtle)', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
            <span style={{ fontSize: '0.85rem', fontWeight: 500, color: 'var(--text-main)' }}>
              {statusSummary.global_description}
            </span>
            <span className="badge badge-up" style={{ fontSize: '0.75rem', padding: '4px 10px' }}>
              {getStatusText(statusSummary.global_indicator)}
            </span>
          </div>

          {/* Component Breakdowns */}
          {statusSummary.components.length > 0 && (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))', gap: '10px' }}>
              {statusSummary.components.map((comp) => (
                <div
                  key={comp.id}
                  style={{ padding: '10px 12px', background: 'var(--bg-subtle)', borderRadius: '8px', border: '1px solid var(--border-color)', display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '12px' }}
                >
                  <span style={{ fontSize: '0.8rem', color: 'var(--text-main)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} title={comp.name}>
                    {comp.name}
                  </span>
                  <span className={`badge ${comp.status === 'operational' ? 'badge-up' : 'badge-warning'}`} style={{ fontSize: '0.7rem', padding: '2px 8px', textTransform: 'uppercase' }}>
                    {comp.status}
                  </span>
                </div>
              ))}
            </div>
          )}

          {/* Active Incidents Banner */}
          {statusSummary.incidents.length > 0 && (
            <div style={{ padding: '10px 14px', background: 'rgba(245, 158, 11, 0.1)', border: '1px solid rgba(245, 158, 11, 0.3)', borderRadius: '8px' }}>
              <span style={{ fontSize: '0.75rem', fontWeight: 'bold', color: '#f59e0b', textTransform: 'uppercase', display: 'block', marginBottom: '4px' }}>
                Active Incident Alert
              </span>
              {statusSummary.incidents.map((inc) => (
                <div key={inc.id} style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                  • <span style={{ fontWeight: 600, color: 'var(--text-main)' }}>{inc.name}</span> ({inc.status})
                </div>
              ))}
            </div>
          )}
        </div>
      ) : null}
    </div>
  );
};
