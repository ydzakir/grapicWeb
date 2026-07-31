from unittest.mock import patch, MagicMock
import pytest
from httpx import ASGITransport, AsyncClient

from main import app
from collectors.cloudflare_collector import CloudflareCollectorAdapter, CloudflareStatusSummary


@pytest.mark.asyncio
async def test_cloudflare_collector_adapter_fallback():
    adapter = CloudflareCollectorAdapter()
    summary = await adapter.fetch_status_summary()
    assert summary is not None
    assert summary.global_indicator in ["none", "minor", "major", "critical"]
    assert len(summary.components) > 0


@pytest.mark.asyncio
async def test_cloudflare_collector_discovery_and_metrics():
    adapter = CloudflareCollectorAdapter()
    discovery = await adapter.discover()
    assert discovery.canonical_identity == "edge-cloudflare-global"
    assert discovery.node_type.value == "service"
    assert len(discovery.connections) == 1

    metrics = await adapter.collect_metrics()
    assert metrics.canonical_identity == "edge-cloudflare-global"
    assert metrics.cpu_usage_percent is not None


@pytest.mark.asyncio
async def test_cloudflare_api_endpoints():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # GET /api/v1/cloudflare/status
        resp = await client.get("/api/v1/cloudflare/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert "global_indicator" in data["data"]

        # GET /api/v1/cloudflare/incidents
        resp_inc = await client.get("/api/v1/cloudflare/incidents")
        assert resp_inc.status_code == 200
        assert "data" in resp_inc.json()

        # POST /api/v1/cloudflare/sync
        resp_sync = await client.post("/api/v1/cloudflare/sync")
        assert resp_sync.status_code == 200
        assert resp_sync.json()["status"] == "success"
