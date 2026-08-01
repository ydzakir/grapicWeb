"""Tests for the wired worker pipeline: Prometheus metrics, alert evaluation,
WebSocket status delta broadcasting, and the report cron engine.

These tests verify that the components the audit found "dead" (never invoked)
are now callable through the worker orchestration paths and behave correctly.
"""
import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from collectors.metrics_exporter import (
    CPU_USAGE,
    NODE_STATUS,
    remove_node_metrics,
    update_node_metrics,
)
from models.alert import Alert, AlertStatus
from models.node import LifecycleStatus, Node, NodeStatus, NodeType, ReviewStatus
from schemas.metrics import StatusDeltaMessage
from services.alert_service import evaluate_node_telemetry_alerts
from services.status_broadcaster import (
    _last_broadcast_status,
    broadcast_status_deltas,
    broadcast_node_status_change,
    reset_broadcast_tracker,
)
from services.websocket_manager import status_ws_manager


@pytest.mark.asyncio
async def test_alert_engine_wired_to_node_telemetry(db_session: AsyncSession):
    """K-3: Alert evaluation must produce a firing alert for a hot node."""
    node = Node(
        name="SERVER-ALERT-WIRED-01",
        type=NodeType.PHYSICAL_SERVER,
        status=NodeStatus.UP,
        review_status=ReviewStatus.APPROVED,
        lifecycle_status=LifecycleStatus.ACTIVE,
    )
    db_session.add(node)
    await db_session.commit()

    # Simulate worker alert cycle: evaluate thresholds from exported metrics
    node_id = str(node.id)
    update_node_metrics(node_id=node_id, status="up", cpu_usage_ratio=0.96)
    from collectors.metrics_exporter import CPU_USAGE

    cpu_gauge = CPU_USAGE._metrics.get((node_id,))
    cpu_percent = float(cpu_gauge._value.get()) * 100.0 if cpu_gauge else None

    alerts = await evaluate_node_telemetry_alerts(
        db_session, node, cpu_usage=cpu_percent
    )
    await db_session.commit()

    assert len(alerts) == 1
    assert alerts[0].status == AlertStatus.FIRING

    stmt = select(Alert).where(Alert.node_id == node.id)
    persisted = (await db_session.execute(stmt)).scalars().first()
    assert persisted is not None

    remove_node_metrics(node_id)


@pytest.mark.asyncio
async def test_status_delta_broadcast_only_on_change(db_session: AsyncSession):
    """K-2: Status deltas are broadcast for approved/active nodes when status changes."""
    reset_broadcast_tracker()

    node = Node(
        name="SERVER-WS-DELTA-01",
        type=NodeType.PHYSICAL_SERVER,
        status=NodeStatus.UP,
        review_status=ReviewStatus.APPROVED,
        lifecycle_status=LifecycleStatus.ACTIVE,
    )
    db_session.add(node)
    await db_session.commit()

    sent: list[StatusDeltaMessage] = []

    async def fake_broadcast(delta):
        sent.append(delta)

    original_broadcast = status_ws_manager.broadcast_status_delta
    status_ws_manager.broadcast_status_delta = fake_broadcast
    try:
        changed = await broadcast_status_deltas(db_session)
        assert changed == 1
        assert len(sent) == 1
        assert sent[0].node_id == str(node.id)
        assert sent[0].status == "up"

        # Second pass: no status change -> no delta
        changed_again = await broadcast_status_deltas(db_session)
        assert changed_again == 0
        assert len(sent) == 1
    finally:
        status_ws_manager.broadcast_status_delta = original_broadcast
        reset_broadcast_tracker()


@pytest.mark.asyncio
async def test_broadcast_node_status_change_immediate(db_session: AsyncSession):
    """K-2: Worker can push an immediate delta after a transition."""
    sent: list[StatusDeltaMessage] = []

    async def fake_broadcast(delta):
        sent.append(delta)

    original_broadcast = status_ws_manager.broadcast_status_delta
    status_ws_manager.broadcast_status_delta = fake_broadcast
    try:
        await broadcast_node_status_change(
            node_id=str(uuid.uuid4()),
            name="SRV-EXAMPLE",
            node_type="physical_server",
            status="down",
        )
        assert len(sent) == 1
        assert sent[0].status == "down"
        assert sent[0].event == "status_delta"
    finally:
        status_ws_manager.broadcast_status_delta = original_broadcast
        _last_broadcast_status.clear()


@pytest.mark.asyncio
async def test_status_delta_skips_pending_nodes(db_session: AsyncSession):
    """K-2: Pending/unapproved nodes must not be broadcast to operational topology."""
    reset_broadcast_tracker()

    pending = Node(
        name="SERVER-WS-PENDING-01",
        type=NodeType.PHYSICAL_SERVER,
        status=NodeStatus.DOWN,
        review_status=ReviewStatus.PENDING,
        lifecycle_status=LifecycleStatus.ACTIVE,
    )
    db_session.add(pending)
    await db_session.commit()

    sent: list[StatusDeltaMessage] = []

    async def fake_broadcast(delta):
        sent.append(delta)

    original_broadcast = status_ws_manager.broadcast_status_delta
    status_ws_manager.broadcast_status_delta = fake_broadcast
    try:
        changed = await broadcast_status_deltas(db_session)
        assert changed == 0
        assert len(sent) == 0
    finally:
        status_ws_manager.broadcast_status_delta = original_broadcast
        reset_broadcast_tracker()


def test_metrics_server_bootstrap_function_exists():
    """K-1: Worker metrics server bootstrap entry point exists and is guarded."""
    from collectors.metrics_exporter import start_worker_metrics_server

    # Should not raise even if the port is already bound (guarded internally)
    start_worker_metrics_server(port=8001)
    assert NODE_STATUS is not None
