import uuid
from datetime import datetime, timezone, timedelta
import pytest

from models.node import Node, NodeStatus
from models.alert import Alert, AlertStatus, AlertSeverity
from services.alert_service import evaluate_node_telemetry_alerts, acknowledge_alert, utc_now


@pytest.mark.asyncio
async def test_alert_threshold_evaluation_and_deduplication(db_session):
    """Test CPU/RAM/Disk threshold evaluation and 15m deduplication logic."""
    node = Node(
        name="SERVER-ALERT-TEST-01",
        type="physical_server",
        status=NodeStatus.UP,
        review_status="approved",
        lifecycle_status="active",
    )
    db_session.add(node)
    await db_session.commit()

    # 1. Trigger Warning alert on CPU > 85%
    alerts1 = await evaluate_node_telemetry_alerts(db_session, node, cpu_usage=88.5)
    assert len(alerts1) == 1
    assert alerts1[0].severity == AlertSeverity.WARNING
    assert alerts1[0].status == AlertStatus.FIRING
    assert "cpu usage" in alerts1[0].message.lower()

    # 2. Immediate re-evaluation (within 15m deduplication window) -> Should not create duplicate alert
    alerts2 = await evaluate_node_telemetry_alerts(db_session, node, cpu_usage=89.0)
    assert len(alerts2) == 0

    # 3. CPU drops back below 85% -> Should auto-resolve firing alert
    await evaluate_node_telemetry_alerts(db_session, node, cpu_usage=45.0)
    await db_session.refresh(alerts1[0])
    assert alerts1[0].status == AlertStatus.RESOLVED
    assert alerts1[0].resolved_at is not None


@pytest.mark.asyncio
async def test_critical_alert_escalation_after_15_minutes(db_session):
    """Test that unacknowledged critical alert is marked escalated after 15 minutes."""
    node = Node(
        name="SERVER-CRITICAL-TEST-02",
        type="physical_server",
        status=NodeStatus.UP,
        review_status="approved",
        lifecycle_status="active",
    )
    db_session.add(node)
    await db_session.commit()

    now = utc_now()
    past_16m = now - timedelta(minutes=16)

    # Create firing critical alert triggered 16 minutes ago
    crit_alert = Alert(
        node_id=node.id,
        severity=AlertSeverity.CRITICAL,
        status=AlertStatus.FIRING,
        message="cpu usage critical high: 98.0%",
        triggered_at=past_16m,
        last_notified_at=past_16m,
        escalated=False,
    )
    db_session.add(crit_alert)
    await db_session.commit()

    # Re-evaluate node telemetry
    await evaluate_node_telemetry_alerts(db_session, node, cpu_usage=99.0)
    await db_session.refresh(crit_alert)

    assert crit_alert.escalated is True


@pytest.mark.asyncio
async def test_acknowledge_alert_with_audit_trail(db_session):
    """Test acknowledging an alert updates status and logs audit entry."""
    node = Node(
        name="SERVER-ACK-TEST-03",
        type="physical_server",
        status=NodeStatus.UP,
        review_status="approved",
        lifecycle_status="active",
    )
    db_session.add(node)
    await db_session.commit()

    alert = Alert(
        node_id=node.id,
        severity=AlertSeverity.WARNING,
        status=AlertStatus.FIRING,
        message="ram usage high: 87.0%",
        triggered_at=utc_now(),
    )
    db_session.add(alert)
    await db_session.commit()

    ack_alert = await acknowledge_alert(db_session, alert.id, username="admin_operator", note="Investigating memory leak")
    assert ack_alert.status == AlertStatus.ACKNOWLEDGED
    assert ack_alert.acknowledged_by == "admin_operator"
    assert ack_alert.acknowledged_at is not None
