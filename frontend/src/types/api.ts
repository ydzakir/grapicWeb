export type NodeType =
  | 'data_center'
  | 'physical_server'
  | 'hyperv_host'
  | 'docker_host'
  | 'hyperv_vm'
  | 'docker_container'
  | 'service';

export type NodeStatus = 'up' | 'down' | 'warning' | 'unknown';
export type ReviewStatus = 'pending' | 'approved' | 'rejected';
export type LifecycleStatus = 'active' | 'archived';
export type UserRole = 'admin' | 'operator' | 'viewer';

export interface User {
  id: string;
  username: string;
  email: string;
  role: UserRole;
  is_active: boolean;
}

export interface NodeItem {
  id: string;
  name: string;
  type: NodeType;
  parent_id: string | null;
  os: string | null;
  cpu_cores: number | null;
  ram_mb: number | null;
  disk_gb: number | null;
  ip_address: string | null;
  status: NodeStatus;
  review_status: ReviewStatus;
  lifecycle_status: LifecycleStatus;
  last_seen: string | null;
  created_at: string;
  updated_at: string;
  metadata: Record<string, any>;
}

export interface PaginatedNodes {
  total: number;
  page: number;
  page_size: number;
  items: NodeItem[];
}

export interface DataCenter {
  id: string;
  name: string;
  type: 'data_center';
  status: NodeStatus;
  review_status: ReviewStatus;
  lifecycle_status: LifecycleStatus;
  metadata: Record<string, any>;
  created_at: string;
  updated_at: string;
}

export interface TopologyNode {
  id: string;
  name: string;
  type: NodeType;
  status: NodeStatus;
  parent_id: string | null;
  review_status: ReviewStatus;
  lifecycle_status: LifecycleStatus;
  ip_address: string | null;
  os: string | null;
  cpu_cores: number | null;
  ram_mb: number | null;
  disk_gb: number | null;
  last_seen?: string | null;
  metadata: Record<string, any>;
}

export interface TopologyEdge {
  id: string;
  source: string;
  target: string;
  connection_type: string;
  metadata: Record<string, any>;
}

export interface TopologyGraph {
  nodes: TopologyNode[];
  edges: TopologyEdge[];
}

export interface MetricDataPoint {
  timestamp: number;
  value: number;
}

export interface MetricSeries {
  node_id: string;
  metric_name: string;
  range: string;
  datapoints: MetricDataPoint[];
}

export interface CollectorTarget {
  id: string;
  name: string;
  target_type: 'ssh' | 'winrm' | 'hyperv' | 'docker';
  host_or_url: string;
  port: number | null;
  credential_reference: string;
  poll_interval_seconds: number;
  is_enabled: boolean;
  last_test_status: string | null;
  last_test_message: string | null;
  created_at: string;
  updated_at: string;
}

export interface StatusDeltaMessage {
  event: 'status_delta';
  node_id: string;
  name: string;
  type: string;
  status: NodeStatus;
  last_seen: string | null;
  timestamp: string;
}

export interface AlertItem {
  id: string;
  node_id: string;
  rule_id: string | null;
  severity: 'warning' | 'critical';
  status: 'firing' | 'resolved' | 'acknowledged';
  message: string;
  triggered_at: string;
  resolved_at: string | null;
  acknowledged_at: string | null;
  acknowledged_by: string | null;
  escalated: boolean;
}

export interface AlertRuleItem {
  id: string;
  node_id: string | null;
  group_name: string | null;
  metric_name: string;
  warning_threshold: number | null;
  critical_threshold: number | null;
  duration_seconds: number;
  is_enabled: boolean;
  created_at: string;
}

export interface CloudflareComponentStatus {
  id: string;
  name: string;
  status: 'operational' | 'degraded_performance' | 'partial_outage' | 'major_outage';
  updated_at?: string;
}

export interface CloudflareIncident {
  id: string;
  name: string;
  status: string;
  impact: 'none' | 'minor' | 'major' | 'critical';
  shortlink?: string;
  created_at?: string;
  updated_at?: string;
}

export interface CloudflareStatusSummary {
  global_indicator: 'none' | 'minor' | 'major' | 'critical';
  global_description: string;
  updated_at: string;
  components: CloudflareComponentStatus[];
  incidents: CloudflareIncident[];
}

