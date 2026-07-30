"""Initial database schema migration for nodes, connections, users, audit logs, and collector targets

Revision ID: 2026_07_30_0001
Revises: 
Create Date: 2026-07-30 23:20:00.000000

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


def upgrade() -> None:
    # Create enum types
    user_role_enum = postgresql.ENUM('admin', 'operator', 'viewer', name='user_role_enum')
    user_role_enum.create(op.get_bind(), checkfirst=True)

    node_type_enum = postgresql.ENUM('data_center', 'physical_server', 'hypervisor_host', 'vm', 'docker_host', 'container', name='node_type_enum')
    node_type_enum.create(op.get_bind(), checkfirst=True)

    node_status_enum = postgresql.ENUM('up', 'down', 'warning', 'unknown', name='node_status_enum')
    node_status_enum.create(op.get_bind(), checkfirst=True)

    review_status_enum = postgresql.ENUM('pending', 'approved', 'rejected', name='review_status_enum')
    review_status_enum.create(op.get_bind(), checkfirst=True)

    lifecycle_status_enum = postgresql.ENUM('active', 'archived', 'deleted', name='lifecycle_status_enum')
    lifecycle_status_enum.create(op.get_bind(), checkfirst=True)

    connection_type_enum = postgresql.ENUM('network', 'hosts', 'depends_on', name='connection_type_enum')
    connection_type_enum.create(op.get_bind(), checkfirst=True)

    target_type_enum = postgresql.ENUM('ssh', 'winrm', 'docker_tls', name='target_type_enum')
    target_type_enum.create(op.get_bind(), checkfirst=True)

    collector_run_status_enum = postgresql.ENUM('success', 'failed', 'timeout', name='collector_run_status_enum')
    collector_run_status_enum.create(op.get_bind(), checkfirst=True)

    # 1. users table
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('username', sa.String(length=64), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('role', sa.Enum('admin', 'operator', 'viewer', name='user_role_enum'), nullable=False, server_default='viewer'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
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
        sa.Column('type', sa.Enum('data_center', 'physical_server', 'hypervisor_host', 'vm', 'docker_host', 'container', name='node_type_enum'), nullable=False),
        sa.Column('parent_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('nodes.id', ondelete='SET NULL'), nullable=True),
        sa.Column('os', sa.String(length=128), nullable=True),
        sa.Column('cpu_cores', sa.Integer(), nullable=True),
        sa.Column('ram_mb', sa.Integer(), nullable=True),
        sa.Column('disk_gb', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('status', sa.Enum('up', 'down', 'warning', 'unknown', name='node_status_enum'), nullable=False, server_default='unknown'),
        sa.Column('review_status', sa.Enum('pending', 'approved', 'rejected', name='review_status_enum'), nullable=False, server_default='pending'),
        sa.Column('lifecycle_status', sa.Enum('active', 'archived', 'deleted', name='lifecycle_status_enum'), nullable=False, server_default='active'),
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
        sa.Column('target_type', sa.Enum('ssh', 'winrm', 'docker_tls', name='target_type_enum'), nullable=False),
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


def downgrade() -> None:
    op.drop_table('audit_logs')
    op.drop_table('collector_runs')
    op.drop_table('collector_targets')
    op.drop_table('node_connections')
    op.drop_table('nodes')
    op.drop_table('users')

    op.execute('DROP TYPE IF EXISTS collector_run_status_enum')
    op.execute('DROP TYPE IF EXISTS target_type_enum')
    op.execute('DROP TYPE IF EXISTS connection_type_enum')
    op.execute('DROP TYPE IF EXISTS lifecycle_status_enum')
    op.execute('DROP TYPE IF EXISTS review_status_enum')
    op.execute('DROP TYPE IF EXISTS node_status_enum')
    op.execute('DROP TYPE IF EXISTS node_type_enum')
    op.execute('DROP TYPE IF EXISTS user_role_enum')
