import uuid
import pytest
import respx
from httpx import ASGITransport, AsyncClient, Response
from starlette.testclient import TestClient

from collectors.metrics_exporter import (
    CPU_USAGE,
    NODE_STATUS,
    RAM_USAGE_PERCENT,
    remove_node_metrics,
    update_node_metrics,
)
from main import app
from models.node import NodeType
from models.user import User, UserRole
from services.node_service import upsert_inventory_node
from services.websocket_manager import status_ws_manager


@pytest.mark.asyncio
async def test_worker_metrics_exporter_and_stale_cleanup():
    test_node_id = str(uuid.uuid4())

    # Update metrics
    update_node_metrics(
        node_id=test_node_id,
        status="up",
        cpu_usage_ratio=0.45,
        ram_usage_percent=62.0,
        disk_usage_percent=45.2,
    )

    # Check metric values in registry
    assert (test_node_id,) in NODE_STATUS._metrics
    assert (test_node_id,) in CPU_USAGE._metrics
    assert (test_node_id,) in RAM_USAGE_PERCENT._metrics
    assert float(CPU_USAGE._metrics[(test_node_id,)]._value.get()) == 0.45

    # Stale series cleanup
    remove_node_metrics(test_node_id)
    assert (test_node_id,) not in NODE_STATUS._metrics


@pytest.mark.asyncio
@respx.mock
async def test_metrics_api_valid_query(db_session):
    admin = User(
        username="m_admin",
        email="madmin@example.com",
        hashed_password="hash",
        role=UserRole.ADMIN,
    )
    db_session.add(admin)
    await db_session.flush()

    node = await upsert_inventory_node(
        db=db_session,
        name="PHYSICAL-DC1-MON-01",
        node_type=NodeType.PHYSICAL_SERVER,
    )
    await db_session.commit()

    # Mock Prometheus HTTP response
    respx.get("http://prometheus:9090/api/v1/query_range").mock(
        return_value=Response(
            200,
            json={
                "status": "success",
                "data": {
                    "resultType": "matrix",
                    "result": [
                        {
                            "metric": {"node_id": str(node.id)},
                            "values": [[1700000000, "45.5"], [1700000060, "50.0"]],
                        }
                    ],
                },
            },
        )
    )

    from core.security import create_access_token
    token = create_access_token(subject=str(admin.id), role=admin.role.value)
    headers = {"Authorization": f"Bearer {token}"}

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get(
            f"/api/v1/metrics?node_id={node.id}&metric_name=cpu_usage&range=1h",
            headers=headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["node_id"] == str(node.id)
        assert body["metric_name"] == "cpu_usage"
        assert len(body["datapoints"]) == 2
        assert body["datapoints"][0]["value"] == 45.5


@pytest.mark.asyncio
async def test_metrics_api_validation_errors(db_session):
    admin = User(
        username="m_val_admin",
        email="mval@example.com",
        hashed_password="hash",
        role=UserRole.ADMIN,
    )
    db_session.add(admin)
    await db_session.flush()

    node = await upsert_inventory_node(
        db=db_session,
        name="PHYSICAL-DC1-MON-02",
        node_type=NodeType.PHYSICAL_SERVER,
    )
    await db_session.commit()

    from core.security import create_access_token
    token = create_access_token(subject=str(admin.id), role=admin.role.value)
    headers = {"Authorization": f"Bearer {token}"}

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        # Invalid metric_name
        resp = await client.get(
            f"/api/v1/metrics?node_id={node.id}&metric_name=invalid_metric",
            headers=headers,
        )
        assert resp.status_code == 400
        assert "not allowed" in resp.json()["error"]["message"].lower()

        # Invalid range
        resp = await client.get(
            f"/api/v1/metrics?node_id={node.id}&range=100y",
            headers=headers,
        )
        assert resp.status_code == 400

        # Non-existent node_id
        random_id = uuid.uuid4()
        resp = await client.get(
            f"/api/v1/metrics?node_id={random_id}",
            headers=headers,
        )
        assert resp.status_code == 404


@pytest.mark.asyncio
@respx.mock
async def test_metrics_api_prometheus_timeout_and_error(db_session):
    admin = User(
        username="m_err_admin",
        email="merr@example.com",
        hashed_password="hash",
        role=UserRole.ADMIN,
    )
    db_session.add(admin)
    await db_session.flush()

    node = await upsert_inventory_node(
        db=db_session,
        name="PHYSICAL-DC1-MON-03",
        node_type=NodeType.PHYSICAL_SERVER,
    )
    await db_session.commit()

    from core.security import create_access_token
    token = create_access_token(subject=str(admin.id), role=admin.role.value)
    headers = {"Authorization": f"Bearer {token}"}

    # Mock Prometheus 500 error
    respx.get("http://prometheus:9090/api/v1/query_range").mock(
        return_value=Response(500, text="Internal Prometheus Error")
    )

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        resp = await client.get(
            f"/api/v1/metrics?node_id={node.id}",
            headers=headers,
        )
        assert resp.status_code == 502


def test_websocket_unauthenticated_rejected():
    client = TestClient(app)
    with pytest.raises(Exception):
        with client.websocket_connect("/ws/status"):
            pass


def test_websocket_authenticated_connection():
    admin_id = str(uuid.uuid4())
    from core.security import create_access_token
    token = create_access_token(subject=admin_id, role="admin")

    client = TestClient(app)
    with client.websocket_connect(f"/ws/status?token={token}") as websocket:
        websocket.send_text("ping")
        data = websocket.receive_text()
        assert data == "pong"
