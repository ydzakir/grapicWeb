import uuid
import pytest
import respx
import httpx
from httpx import Response
from fastapi.testclient import TestClient

from main import app
from models.node import Node, NodeStatus
from services.metrics_service import query_node_metrics
from services.collector_service import process_collector_failure


client = TestClient(app)


@pytest.mark.asyncio
async def test_prometheus_timeout_raises_timeout_error(db_session):
    """Test that when Prometheus times out, query_node_metrics raises TimeoutError."""
    prometheus_url = "http://prometheus:9090"
    node_id = uuid.uuid4()
    node = Node(
        id=node_id,
        name="TEST-FAIL-NODE-01",
        type="physical_server",
        status=NodeStatus.UP,
        review_status="approved",
        lifecycle_status="active",
    )
    db_session.add(node)
    await db_session.commit()

    with respx.mock:
        respx.get(f"{prometheus_url}/api/v1/query_range").mock(
            side_effect=httpx.TimeoutException("Prometheus connection timeout")
        )

        async with httpx.AsyncClient() as http_client:
            with pytest.raises(TimeoutError):
                await query_node_metrics(
                    db=db_session,
                    node_id=node_id,
                    metric_name="cpu_usage",
                    range_str="1h",
                    client=http_client,
                )


@pytest.mark.asyncio
async def test_prometheus_http_error_raises_runtime_error(db_session):
    """Test that when Prometheus returns 500/502, query_node_metrics raises RuntimeError."""
    prometheus_url = "http://prometheus:9090"
    node_id = uuid.uuid4()
    node = Node(
        id=node_id,
        name="TEST-FAIL-NODE-02",
        type="physical_server",
        status=NodeStatus.UP,
        review_status="approved",
        lifecycle_status="active",
    )
    db_session.add(node)
    await db_session.commit()

    with respx.mock:
        respx.get(f"{prometheus_url}/api/v1/query_range").mock(
            return_value=Response(500, text="Internal Server Error")
        )

        async with httpx.AsyncClient() as http_client:
            with pytest.raises(RuntimeError):
                await query_node_metrics(
                    db=db_session,
                    node_id=node_id,
                    metric_name="cpu_usage",
                    range_str="1h",
                    client=http_client,
                )


@pytest.mark.asyncio
async def test_collector_transient_failure_handling(db_session):
    """Test that collector target connection failure updates node status cleanly."""
    canonical_id = "test-canonical-unreachable-01"
    node = Node(
        name="UNREACHABLE-HOST-01",
        type="physical_server",
        status=NodeStatus.UP,
        review_status="approved",
        lifecycle_status="active",
        metadata_={"canonical_identity": canonical_id},
    )
    db_session.add(node)
    await db_session.commit()

    # Process failure with error message
    updated_node = await process_collector_failure(db_session, canonical_id, "Connection timed out after 10s")
    assert updated_node is not None
    assert updated_node.status in (NodeStatus.DOWN, NodeStatus.WARNING, NodeStatus.UNKNOWN)


def test_health_liveness_and_readiness():
    """Test liveness and readiness health probe endpoints."""
    live_resp = client.get("/api/v1/health/live")
    assert live_resp.status_code == 200
    assert live_resp.json()["status"] == "live"

    ready_resp = client.get("/api/v1/health/ready")
    assert ready_resp.status_code == 200
    assert ready_resp.json()["status"] == "ready"
