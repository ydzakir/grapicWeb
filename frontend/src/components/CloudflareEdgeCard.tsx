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

  const getBadgeClass = (indicator?: string) => {
    switch (indicator) {
      case 'none':
        return 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30';
      case 'minor':
        return 'bg-amber-500/20 text-amber-400 border-amber-500/30';
      case 'major':
      case 'critical':
        return 'bg-rose-500/20 text-rose-400 border-rose-500/30';
      default:
        return 'bg-slate-500/20 text-slate-400 border-slate-500/30';
    }
  };

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
    <div className="bg-slate-900/80 backdrop-blur border border-slate-800 rounded-xl p-5 shadow-lg">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-orange-500/10 border border-orange-500/20 flex items-center justify-center text-orange-400 font-bold text-lg">
            CF
          </div>
          <div>
            <h3 className="text-base font-semibold text-slate-100 flex items-center gap-2">
              Cloudflare Edge Status
            </h3>
            <p className="text-xs text-slate-400">Global CDN, WAF & Anycast Network Probe</p>
          </div>
        </div>
        <button
          onClick={handleSync}
          disabled={syncing}
          className="px-3 py-1.5 text-xs font-medium text-slate-300 bg-slate-800 hover:bg-slate-700 border border-slate-700 rounded-lg transition-all flex items-center gap-1.5 disabled:opacity-50"
        >
          {syncing ? (
            <>
              <span className="w-3 h-3 border-2 border-slate-400 border-t-transparent rounded-full animate-spin"></span>
              Syncing...
            </>
          ) : (
            'Sync Now'
          )}
        </button>
      </div>

      {loading ? (
        <div className="py-6 text-center text-slate-400 text-sm animate-pulse">
          Probing Cloudflare Edge Status...
        </div>
      ) : error ? (
        <div className="p-3 bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs rounded-lg">
          {error}
        </div>
      ) : statusSummary ? (
        <div className="space-y-4">
          <div className="flex items-center justify-between p-3 bg-slate-800/50 rounded-lg border border-slate-800">
            <span className="text-sm font-medium text-slate-300">
              {statusSummary.global_description}
            </span>
            <span
              className={`px-2.5 py-1 text-xs font-semibold rounded-full border ${getBadgeClass(
                statusSummary.global_indicator
              )}`}
            >
              {getStatusText(statusSummary.global_indicator)}
            </span>
          </div>

          {/* Component Breakdowns */}
          {statusSummary.components.length > 0 && (
            <div className="grid grid-cols-2 gap-2">
              {statusSummary.components.map((comp) => (
                <div
                  key={comp.id}
                  className="p-2.5 bg-slate-800/30 rounded-lg border border-slate-800/80 flex items-center justify-between"
                >
                  <span className="text-xs text-slate-300 truncate pr-2" title={comp.name}>
                    {comp.name}
                  </span>
                  <span
                    className={`text-[10px] font-semibold px-2 py-0.5 rounded border ${
                      comp.status === 'operational'
                        ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                        : 'bg-amber-500/10 text-amber-400 border-amber-500/20'
                    }`}
                  >
                    {comp.status}
                  </span>
                </div>
              ))}
            </div>
          )}

          {/* Active Incidents Banner */}
          {statusSummary.incidents.length > 0 && (
            <div className="p-3 bg-amber-500/10 border border-amber-500/30 rounded-lg space-y-1">
              <span className="text-xs font-bold text-amber-400 uppercase tracking-wider block">
                Active Incident Alert
              </span>
              {statusSummary.incidents.map((inc) => (
                <div key={inc.id} className="text-xs text-slate-300">
                  • <span className="font-semibold text-slate-200">{inc.name}</span> ({inc.status})
                </div>
              ))}
            </div>
          )}
        </div>
      ) : null}
    </div>
  );
};
