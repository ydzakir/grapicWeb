import uuid
import pytest
import httpx
from httpx import AsyncClient
from main import app
from models.node import Node, NodeStatus
from models.alert import Alert, AlertSeverity, AlertStatus
from models.user import User, UserRole
from core.security import create_access_token


@pytest.mark.asyncio
async def test_alert_api_active_history_and_acknowledge(db_session):
    admin = User(
        username="admin_alert_api",
        email="admin_alert_api@infra.com",
        hashed_password="hash",
        role=UserRole.ADMIN,
        is_active=True,
    )
    db_session.add(admin)
    await db_session.commit()

    token = create_access_token(subject=str(admin.id), role=admin.role.value)
    headers = {"Authorization": f"Bearer {token}"}

    node = Node(
        name="SERVER-API-TEST-01",
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
        message="disk usage high: 82.5%",
        triggered_at=node.created_at,
    )
    db_session.add(alert)
    await db_session.commit()

    async with AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
        # GET Active Alerts
        resp = await ac.get("/api/v1/alerts/active", headers=headers)
        assert resp.status_code == 200
        active_list = resp.json()
        assert len(active_list) >= 1
        assert active_list[0]["status"] == "firing"

        # POST Acknowledge Alert
        ack_resp = await ac.post(
            f"/api/v1/alerts/{alert.id}/acknowledge",
            json={"note": "Acknowledged in test"},
            headers=headers,
        )
        assert ack_resp.status_code == 200
        assert ack_resp.json()["status"] == "acknowledged"

        # GET History
        hist_resp = await ac.get("/api/v1/alerts/history", headers=headers)
        assert hist_resp.status_code == 200
        hist_list = hist_resp.json()
        assert len(hist_list) >= 1
