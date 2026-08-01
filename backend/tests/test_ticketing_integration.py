import pytest
from datetime import datetime, timezone
from httpx import AsyncClient

from core.security import create_access_token
from models.alert import Alert, AlertSeverity, AlertStatus
from models.node import Node, NodeStatus, NodeType
from models.user import User, UserRole


@pytest.mark.asyncio
async def test_create_ticket_for_alert_jira_mock(async_client: AsyncClient, db_session):
    """Test manual ITSM ticket creation for an alert (Jira mock)."""
    admin = User(
        username="admin_jira_test",
        email="admin_jira@infra.com",
        hashed_password="hash",
        role=UserRole.ADMIN,
        is_active=True,
    )
    db_session.add(admin)
    await db_session.commit()
    token = create_access_token(subject=str(admin.id), role=admin.role.value)
    headers = {"Authorization": f"Bearer {token}"}

    node = Node(name="jira-test-node", ip_address="10.0.0.88", type=NodeType.SERVER, status=NodeStatus.ONLINE)
    db_session.add(node)
    await db_session.commit()

    alert = Alert(
        node_id=node.id,
        severity=AlertSeverity.CRITICAL,
        status=AlertStatus.FIRING,
        message="CPU Usage Critical 98%",
        triggered_at=datetime.now(timezone.utc),
    )
    db_session.add(alert)
    await db_session.commit()

    # Call POST /api/v1/alerts/{alert_id}/ticket
    response = await async_client.post(
        f"/api/v1/alerts/{alert.id}/ticket",
        json={
            "system_type": "jira",
            "project_key": "PROJ",
            "issue_type": "Incident",
            "summary": "Critical CPU issue",
        },
        headers=headers,
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["ticket_id"] is not None
    assert data["ticket_system"] == "jira"
    assert data["ticket_status"] == "OPEN"
    assert "PROJ" in data["ticket_id"]
    assert data["ticket_url"] is not None


@pytest.mark.asyncio
async def test_sync_ticket_status(async_client: AsyncClient, db_session):
    """Test synchronizing ticket status with external ITSM system."""
    admin = User(
        username="admin_snow_test",
        email="admin_snow@infra.com",
        hashed_password="hash",
        role=UserRole.ADMIN,
        is_active=True,
    )
    db_session.add(admin)
    await db_session.commit()
    token = create_access_token(subject=str(admin.id), role=admin.role.value)
    headers = {"Authorization": f"Bearer {token}"}

    node = Node(name="snow-test-node", ip_address="10.0.0.89", type=NodeType.SERVER, status=NodeStatus.ONLINE)
    db_session.add(node)
    await db_session.commit()

    alert = Alert(
        node_id=node.id,
        severity=AlertSeverity.WARNING,
        status=AlertStatus.FIRING,
        message="RAM Usage Warning 88%",
        triggered_at=datetime.now(timezone.utc),
        ticket_id="INC009999",
        ticket_system="servicenow",
        ticket_status="OPEN",
        ticket_url="https://servicenow.example.com/incident/INC009999",
    )
    db_session.add(alert)
    await db_session.commit()

    response = await async_client.post(
        f"/api/v1/alerts/{alert.id}/sync-ticket",
        headers=headers,
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["ticket_id"] == "INC009999"
    assert data["ticket_status"] is not None


@pytest.mark.asyncio
async def test_ticket_webhook_callback(async_client: AsyncClient, db_session):
    """Test receiving incoming webhook status updates from Jira / ServiceNow."""
    node = Node(name="webhook-test-node", ip_address="10.0.0.90", type=NodeType.SERVER, status=NodeStatus.ONLINE)
    db_session.add(node)
    await db_session.commit()

    alert = Alert(
        node_id=node.id,
        severity=AlertSeverity.CRITICAL,
        status=AlertStatus.FIRING,
        message="Disk Usage Critical 95%",
        triggered_at=datetime.now(timezone.utc),
        ticket_id="INC-CALLBACK-123",
        ticket_system="jira",
        ticket_status="IN_PROGRESS",
    )
    db_session.add(alert)
    await db_session.commit()

    # Webhook updates status to RESOLVED
    callback_payload = {
        "alert_id": str(alert.id),
        "ticket_id": "INC-CALLBACK-123",
        "ticket_status": "RESOLVED",
        "notes": "Issue resolved by SysAdmin in Jira",
    }

    response = await async_client.post("/api/v1/alerts/tickets/webhook-callback", json=callback_payload)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["status"] == "success"
    assert data["ticket_status"] == "RESOLVED"

    # Verify Alert status is auto-resolved
    await db_session.refresh(alert)
    assert alert.ticket_status == "RESOLVED"
    assert alert.status == AlertStatus.RESOLVED
    assert alert.resolved_at is not None
