import asyncio

import pytest

from collectors.base import NormalizedDiscoveryResult, NormalizedMetricsResult
from collectors.fake_collector import FakeCollectorAdapter
from core.secrets import EnvironmentAndFileSecretProvider
from models.node import NodeType


@pytest.mark.asyncio
async def test_fake_collector_adapter_discovery_and_metrics():
    adapter = FakeCollectorAdapter(target_host="test-host-01")

    assert await adapter.test_connection() is True

    discovery = await adapter.discover()
    assert isinstance(discovery, NormalizedDiscoveryResult)
    assert discovery.canonical_identity == "fake_host_test-host-01"
    assert discovery.node_type == NodeType.PHYSICAL_SERVER
    assert len(discovery.children) == 2

    # Verify child types
    types = [child.node_type for child in discovery.children]
    assert NodeType.HYPERV_VM in types
    assert NodeType.DOCKER_CONTAINER in types

    metrics = await adapter.collect_metrics()
    assert isinstance(metrics, NormalizedMetricsResult)
    assert metrics.cpu_usage_percent == 35.5
    assert metrics.ram_usage_percent == 62.0


@pytest.mark.asyncio
async def test_fake_collector_failure_modes():
    # Timeout mode
    timeout_adapter = FakeCollectorAdapter(simulate_failure_mode="timeout")
    with pytest.raises(asyncio.TimeoutError):
        await timeout_adapter.test_connection()
    with pytest.raises(asyncio.TimeoutError):
        await timeout_adapter.discover()
    with pytest.raises(asyncio.TimeoutError):
        await timeout_adapter.collect_metrics()

    # Connection refused mode
    refused_adapter = FakeCollectorAdapter(simulate_failure_mode="connection_refused")
    with pytest.raises(ConnectionRefusedError):
        await refused_adapter.discover()


def test_secret_provider_environment_fallback(monkeypatch):
    provider = EnvironmentAndFileSecretProvider()
    monkeypatch.setenv("MY_SSH_KEY", "secret_ssh_passphrase_123")

    # Clean reference
    resolved = provider.get_secret("docker_secret:MY_SSH_KEY")
    assert resolved == "secret_ssh_passphrase_123"

    # Non-existent reference returns None
    assert provider.get_secret("NON_EXISTENT_REF_KEY") is None
