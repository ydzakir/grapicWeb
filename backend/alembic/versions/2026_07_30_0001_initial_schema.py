"""Initial database schema migration for the full Infrastructure Monitoring application.

Revision ID: 2026_07_30_0001
Revises:
Create Date: 2026-07-30 23:20:00.000000

NOTE: This migration was rewritten (2026-08-02) to reflect the ACTUAL model schema
used by the application. The previous version only created 6 tables and used enum
values that did not match the SQLAlchemy models (e.g. 'hypervisor_host'/'vm' vs the
real 'hyperv_host'/'hyperv_vm'), which caused `alembic upgrade head` on an empty
PostgreSQL to produce an inconsistent database and 500 errors on alert/network/
governance/topology-history endpoints. This version creates the complete schema:
users, nodes, node_connections, collector_targets, collector_runs, audit_logs,
alert_rules, alerts, notification_providers, subnets, network_edges, report_schedules,
quarterly_audit_reviews, topology_snapshots, and topology_change_logs.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '2026_07_30_0001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _create_enums() -> None:
    """Create all PostgreSQL enum types used by the models."""
    postgresql.ENUM('admin', 'operator', 'viewer', name='user_role_enum').create(op.get_bind(), checkfirst=True)
    postgresql.ENUM(
        'data_center', 'physical_server', 'hyperv_host', 'hyperv_vm',
        'docker_host', 'docker_container', 'service',
        name='node_type_enum',
    ).create(op.get_bind(), checkfirst=True)
    postgresql.ENUM('up', 'down', 'warning', 'unknown', name='node_status_enum').create(op.get_bind(), checkfirst=True)
    postgresql.ENUM('pending', 'approved', 'rejected', name='review_status_enum').create(op.get_bind(), checkfirst=True)
    postgresql.ENUM('active', 'archived', name='lifecycle_status_enum').create(op.get_bind(), checkfirst=True)
    postgresql.ENUM('network', 'hosts', 'depends_on', name='connection_type_enum').create(op.get_bind(), checkfirst=True)
    postgresql.ENUM('ssh', 'winrm', 'docker_tls', 'fake', name='target_type_enum').create(op.get_bind(), checkfirst=True)
    postgresql.ENUM('success', 'failed', 'timeout', name='collector_run_status_enum').create(op.get_bind(), checkfirst=True)
    postgresql.ENUM('warning', 'critical', name='alert_severity_enum').create(op.get_bind(), checkfirst=True)
    postgresql.ENUM('firing', 'resolved', 'acknowledged', name='alert_status_enum').create(op.get_bind(), checkfirst=True)
    postgresql.ENUM('high', 'medium', 'manual', name='edge_confidence_level_enum').create(op.get_bind(), checkfirst=True)


def upgrade() -> None:
    _create_enums()

    # 1. users table
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('username', sa.String(length=64), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('role', sa.Enum('admin', 'operator', 'viewer', name='user_role_enum'), nullable=False, server_default='viewer'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('custom_permissions', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('allowed_group_scopes', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_users_username', 'users', ['username'], unique=True)
    op.create_index('ix_users_email', 'users', ['email'], unique=True)
    op.create_index('ix_users_role', 'users', ['role'], unique=False)

    # 2. nodes table
    op.create_table(
        'nodes',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column(
            'type',
            sa.Enum(
                'data_center', 'physical_server', 'hyperv_host', 'hyperv_vm',
                'docker_host', 'docker_container', 'service',
                name='node_type_enum',
            ),
            nullable=False,
        ),
        sa.Column('parent_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('nodes.id', ondelete='SET NULL'), nullable=True),
        sa.Column('os', sa.String(length=128), nullable=True),
        sa.Column('cpu_cores', sa.Integer(), nullable=True),
        sa.Column('ram_mb', sa.Integer(), nullable=True),
        sa.Column('disk_gb', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('status', sa.Enum('up', 'down', 'warning', 'unknown', name='node_status_enum'), nullable=False, server_default='unknown'),
        sa.Column('review_status', sa.Enum('pending', 'approved', 'rejected', name='review_status_enum'), nullable=False, server_default='pending'),
        sa.Column('lifecycle_status', sa.Enum('active', 'archived', name='lifecycle_status_enum'), nullable=False, server_default='active'),
        sa.Column('last_seen', sa.DateTime(timezone=True), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_nodes_name', 'nodes', ['name'], unique=False)
    op.create_index('ix_nodes_type', 'nodes', ['type'], unique=False)
    op.create_index('ix_nodes_parent_id', 'nodes', ['parent_id'], unique=False)
    op.create_index('ix_nodes_ip_address', 'nodes', ['ip_address'], unique=False)
    op.create_index('ix_nodes_status', 'nodes', ['status'], unique=False)
    op.create_index('ix_nodes_review_status', 'nodes', ['review_status'], unique=False)
    op.create_index('ix_nodes_lifecycle_status', 'nodes', ['lifecycle_status'], unique=False)
    op.create_index('idx_nodes_type_status', 'nodes', ['type', 'status'], unique=False)
    op.create_index('idx_nodes_review_lifecycle', 'nodes', ['review_status', 'lifecycle_status'], unique=False)

    # 3. node_connections table
    op.create_table(
        'node_connections',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('source_node_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('nodes.id', ondelete='CASCADE'), nullable=False),
        sa.Column('target_node_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('nodes.id', ondelete='CASCADE'), nullable=False),
        sa.Column('connection_type', sa.Enum('network', 'hosts', 'depends_on', name='connection_type_enum'), nullable=False, server_default='depends_on'),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('source_node_id', 'target_node_id', 'connection_type', name='uq_node_connection_edge'),
    )
    op.create_index('ix_node_connections_source_node_id', 'node_connections', ['source_node_id'], unique=False)
    op.create_index('ix_node_connections_target_node_id', 'node_connections', ['target_node_id'], unique=False)

    # 4. collector_targets table
    op.create_table(
        'collector_targets',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('name', sa.String(length=128), nullable=False),
        sa.Column('target_type', sa.Enum('ssh', 'winrm', 'docker_tls', 'fake', name='target_type_enum'), nullable=False),
        sa.Column('host', sa.String(length=255), nullable=False),
        sa.Column('port', sa.Integer(), nullable=False),
        sa.Column('credential_reference', sa.String(length=255), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_collector_targets_target_type', 'collector_targets', ['target_type'], unique=False)

    # 5. collector_runs table
    op.create_table(
        'collector_runs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('target_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('collector_targets.id', ondelete='CASCADE'), nullable=False),
        sa.Column('status', sa.Enum('success', 'failed', 'timeout', name='collector_run_status_enum'), nullable=False),
        sa.Column('consecutive_failures', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('first_failure_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_attempt_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_collector_runs_target_id', 'collector_runs', ['target_id'], unique=False)

    # 6. audit_logs table
    op.create_table(
        'audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('actor_username', sa.String(length=64), nullable=False),
        sa.Column('action', sa.String(length=128), nullable=False),
        sa.Column('target', sa.String(length=255), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
    )
    op.create_index('ix_audit_logs_actor_username', 'audit_logs', ['actor_username'], unique=False)
    op.create_index('ix_audit_logs_action', 'audit_logs', ['action'], unique=False)
    op.create_index('ix_audit_logs_timestamp', 'audit_logs', ['timestamp'], unique=False)

    # 7. alert_rules table
    op.create_table(
        'alert_rules',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('node_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('nodes.id', ondelete='CASCADE'), nullable=True),
        sa.Column('group_name', sa.String(length=64), nullable=True),
        sa.Column('metric_name', sa.String(length=64), nullable=False),
        sa.Column('warning_threshold', sa.Float(), nullable=True),
        sa.Column('critical_threshold', sa.Float(), nullable=True),
        sa.Column('duration_seconds', sa.Integer(), nullable=False, server_default='300'),
        sa.Column('is_enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_alert_rules_node_id', 'alert_rules', ['node_id'], unique=False)
    op.create_index('ix_alert_rules_group_name', 'alert_rules', ['group_name'], unique=False)

    # 8. alerts table
    op.create_table(
        'alerts',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('node_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('nodes.id', ondelete='CASCADE'), nullable=False),
        sa.Column('rule_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('alert_rules.id', ondelete='SET NULL'), nullable=True),
        sa.Column('severity', sa.Enum('warning', 'critical', name='alert_severity_enum'), nullable=False),
        sa.Column('status', sa.Enum('firing', 'resolved', 'acknowledged', name='alert_status_enum'), nullable=False, server_default='firing'),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('triggered_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('acknowledged_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('acknowledged_by', sa.String(length=64), nullable=True),
        sa.Column('last_notified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('escalated', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('ticket_id', sa.String(length=64), nullable=True),
        sa.Column('ticket_url', sa.String(length=256), nullable=True),
        sa.Column('ticket_system', sa.String(length=32), nullable=True),
        sa.Column('ticket_status', sa.String(length=32), nullable=True),
        sa.Column('ticket_created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_alerts_node_id', 'alerts', ['node_id'], unique=False)
    op.create_index('ix_alerts_severity', 'alerts', ['severity'], unique=False)
    op.create_index('ix_alerts_status', 'alerts', ['status'], unique=False)
    op.create_index('ix_alerts_ticket_id', 'alerts', ['ticket_id'], unique=False)
    op.create_index('idx_alerts_status_severity', 'alerts', ['status', 'severity'], unique=False)

    # 9. notification_providers table
    op.create_table(
        'notification_providers',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('name', sa.String(length=64), nullable=False),
        sa.Column('provider_type', sa.String(length=32), nullable=False),
        sa.Column('config', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('is_enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )

    # 10. subnets table
    op.create_table(
        'subnets',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('cidr', sa.String(length=64), nullable=False, unique=True),
        sa.Column('vlan_id', sa.Integer(), nullable=True),
        sa.Column('name', sa.String(length=128), nullable=False),
        sa.Column('provenance', sa.String(length=64), nullable=False, server_default='snmp_discovery'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_subnets_cidr', 'subnets', ['cidr'], unique=True)

    # 11. network_edges table
    op.create_table(
        'network_edges',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('source_node_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('nodes.id', ondelete='CASCADE'), nullable=False),
        sa.Column('target_node_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('nodes.id', ondelete='CASCADE'), nullable=False),
        sa.Column('connection_type', sa.String(length=64), nullable=False, server_default='network_link'),
        sa.Column('provenance', sa.String(length=64), nullable=False, server_default='arp_discovery'),
        sa.Column('confidence_level', sa.Enum('high', 'medium', 'manual', name='edge_confidence_level_enum'), nullable=False, server_default='medium'),
        sa.Column('has_active_traffic', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('last_verified_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('idx_network_edges_source_target', 'network_edges', ['source_node_id', 'target_node_id'], unique=True)
    op.create_index('ix_network_edges_source_node_id', 'network_edges', ['source_node_id'], unique=False)
    op.create_index('ix_network_edges_target_node_id', 'network_edges', ['target_node_id'], unique=False)

    # 12. report_schedules table
    op.create_table(
        'report_schedules',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('name', sa.String(length=128), nullable=False),
        sa.Column('frequency', sa.String(length=32), nullable=False, server_default='weekly'),
        sa.Column('report_type', sa.String(length=32), nullable=False, server_default='weekly'),
        sa.Column('export_format', sa.String(length=32), nullable=False, server_default='pdf'),
        sa.Column('recipients', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('is_enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('last_run_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('next_run_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )

    # 13. quarterly_audit_reviews table
    op.create_table(
        'quarterly_audit_reviews',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('quarter', sa.String(length=32), nullable=False),
        sa.Column('title', sa.String(length=128), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='IN_REVIEW'),
        sa.Column('reviewer_username', sa.String(length=64), nullable=False),
        sa.Column('due_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('user_snapshots', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('review_decisions', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('signoff_by', sa.String(length=64), nullable=True),
        sa.Column('signoff_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('digital_signature', sa.String(length=128), nullable=True),
        sa.Column('comments', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_quarterly_audit_reviews_quarter', 'quarterly_audit_reviews', ['quarter'], unique=False)
    op.create_index('ix_quarterly_audit_reviews_status', 'quarterly_audit_reviews', ['status'], unique=False)
    op.create_index('ix_quarterly_audit_reviews_reviewer_username', 'quarterly_audit_reviews', ['reviewer_username'], unique=False)

    # 14. topology_snapshots table
    op.create_table(
        'topology_snapshots',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('node_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('edge_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('graph_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
    )
    op.create_index('ix_topology_snapshots_timestamp', 'topology_snapshots', ['timestamp'], unique=False)

    # 15. topology_change_logs table
    op.create_table(
        'topology_change_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('action', sa.String(length=64), nullable=False),
        sa.Column('entity_type', sa.String(length=64), nullable=False),
        sa.Column('entity_id', sa.String(length=128), nullable=False),
        sa.Column('details', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
    )
    op.create_index('ix_topology_change_logs_timestamp', 'topology_change_logs', ['timestamp'], unique=False)
    op.create_index('ix_topology_change_logs_action', 'topology_change_logs', ['action'], unique=False)


def downgrade() -> None:
    op.drop_table('topology_change_logs')
    op.drop_table('topology_snapshots')
    op.drop_table('quarterly_audit_reviews')
    op.drop_table('report_schedules')
    op.drop_table('network_edges')
    op.drop_table('subnets')
    op.drop_table('notification_providers')
    op.drop_table('alerts')
    op.drop_table('alert_rules')
    op.drop_table('audit_logs')
    op.drop_table('collector_runs')
    op.drop_table('collector_targets')
    op.drop_table('node_connections')
    op.drop_table('nodes')
    op.drop_table('users')

    op.execute('DROP TYPE IF EXISTS edge_confidence_level_enum')
    op.execute('DROP TYPE IF EXISTS alert_status_enum')
    op.execute('DROP TYPE IF EXISTS alert_severity_enum')
    op.execute('DROP TYPE IF EXISTS collector_run_status_enum')
    op.execute('DROP TYPE IF EXISTS target_type_enum')
    op.execute('DROP TYPE IF EXISTS connection_type_enum')
    op.execute('DROP TYPE IF EXISTS lifecycle_status_enum')
    op.execute('DROP TYPE IF EXISTS review_status_enum')
    op.execute('DROP TYPE IF EXISTS node_status_enum')
    op.execute('DROP TYPE IF EXISTS node_type_enum')
    op.execute('DROP TYPE IF EXISTS user_role_enum')
