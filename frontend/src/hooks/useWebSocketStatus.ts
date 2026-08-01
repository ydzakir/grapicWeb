import { useEffect, useRef, useState, useCallback } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { StatusDeltaMessage, TopologyGraph } from '../types/api';
import { useAuth } from '../context/AuthContext';

export function useWebSocketStatus() {
  const { token, isAuthenticated } = useAuth();
  const queryClient = useQueryClient();
  const [connectionStatus, setConnectionStatus] = useState<'connected' | 'connecting' | 'disconnected'>('disconnected');
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const retryCountRef = useRef(0);

  const connect = useCallback(() => {
    if (!isAuthenticated || !token) {
      setConnectionStatus('disconnected');
      return;
    }

    setConnectionStatus('connecting');
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/api/v1/ws/status?token=${encodeURIComponent(token)}`;

    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      setConnectionStatus('connected');
      retryCountRef.current = 0;
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data) as StatusDeltaMessage;
        if (data && data.event === 'status_delta' && data.node_id) {
          // Update topology graph cache directly without refetching entire graph
          queryClient.setQueriesData<TopologyGraph>({ queryKey: ['topology'] }, (oldGraph) => {
            if (!oldGraph) return oldGraph;
            return {
              ...oldGraph,
              nodes: oldGraph.nodes.map((node) =>
                node.id === data.node_id
                  ? { ...node, status: data.status, last_seen: data.last_seen || node.last_seen }
                  : node
              ),
            };
          });

          // Invalidate node list queries to keep table synced
          queryClient.invalidateQueries({ queryKey: ['nodes'] });
        }
      } catch (err) {
        // Ignore ping/non-json messages
      }
    };

    ws.onclose = () => {
      setConnectionStatus('disconnected');
      wsRef.current = null;

      // Exponential backoff reconnect: 1s, 2s, 4s, 8s, 16s max
      const backoffMs = Math.min(1000 * Math.pow(2, retryCountRef.current), 16000);
      retryCountRef.current += 1;

      reconnectTimeoutRef.current = setTimeout(() => {
        connect();
      }, backoffMs);
    };

    ws.onerror = () => {
      ws.close();
    };
  }, [token, isAuthenticated, queryClient]);

  useEffect(() => {
    connect();

    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [connect]);

  return { connectionStatus };
}
