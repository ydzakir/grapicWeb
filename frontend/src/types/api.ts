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
  ticket_id?: string | null;
  ticket_url?: string | null;
  ticket_system?: string | null;
  ticket_status?: string | null;
  ticket_created_at?: string | null;
}

export interface CreateTicketPayload {
  system_type: 'jira' | 'servicenow' | 'itsm_webhook';
  project_key?: string;
  issue_type?: string;
  urgency?: string;
  summary?: string;
  description?: string;
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

export interface UserSnapshotItem {
  user_id: string;
  username: string;
  email: string;
  role: string;
  is_active: boolean;
  snapshot_at: string;
}

export interface ReviewDecisionItem {
  user_id: string;
  decision: 'approve' | 'revoke' | 'modify_role';
  new_role?: string | null;
  notes?: string | null;
  reviewed_by: string;
  reviewed_at: string;
}

export interface QuarterlyAuditReviewItem {
  id: string;
  quarter: string;
  title: string;
  status: 'IN_REVIEW' | 'APPROVED' | 'REJECTED' | 'OVERDUE_ESCALATED';
  reviewer_username: string;
  due_date: string;
  user_snapshots: Record<string, UserSnapshotItem>;
  review_decisions: Record<string, ReviewDecisionItem>;
  signoff_by?: string | null;
  signoff_at?: string | null;
  digital_signature?: string | null;
  comments?: string | null;
  created_at: string;
}

export interface ComplianceReportData {
  review_id: string;
  quarter: string;
  title: string;
  status: string;
  total_accounts: number;
  approved_accounts: number;
  revoked_accounts: number;
  modified_accounts: number;
  pending_accounts: number;
  compliance_percentage: number;
  signoff_by?: string | null;
  signoff_at?: string | null;
  digital_signature?: string | null;
  generated_at: string;
}

export interface ReportScheduleItem {
  id: string;
  name: string;
  frequency: 'daily' | 'weekly' | 'monthly';
  report_type: 'weekly' | 'monthly';
  export_format: 'pdf' | 'excel' | 'both';
  recipients: string[];
  is_enabled: boolean;
  last_run_at?: string | null;
  next_run_at?: string | null;
  created_at: string;
}

export interface CreateReportSchedulePayload {
  name: string;
  frequency: 'daily' | 'weekly' | 'monthly';
  report_type: 'weekly' | 'monthly';
  export_format: 'pdf' | 'excel' | 'both';
  recipients: string[];
  is_enabled?: boolean;
}

export interface UserDetailItem {
  id: string;
  username: string;
  email: string;
  role: 'admin' | 'operator' | 'viewer';
  is_active: boolean;
  custom_permissions: { permissions: string[] };
  allowed_group_scopes: { scopes: string[] };
  created_at: string;
}

export interface CreateUserPayload {
  username: string;
  email: string;
  password: string;
  role: 'admin' | 'operator' | 'viewer';
  custom_permissions?: string[];
  allowed_group_scopes?: string[];
  is_active?: boolean;
}

export interface UpdateUserPayload {
  email?: string;
  password?: string;
  role?: 'admin' | 'operator' | 'viewer';
  custom_permissions?: string[];
  allowed_group_scopes?: string[];
  is_active?: boolean;
}


