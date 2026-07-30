from abc import ABC, abstractmethod
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field

from models.node import NodeType


def utc_now() -> datetime:
    return datetime.now(UTC)


class NormalizedConnectionResult(BaseModel):
    target_canonical_identity: str
    connection_type: str = "network"
    metadata: dict[str, Any] = Field(default_factory=dict)


class NormalizedDiscoveryResult(BaseModel):
    canonical_identity: str
    name: str
    node_type: NodeType
    ip_address: str | None = None
    os: str | None = None
    cpu_cores: int | None = None
    ram_mb: int | None = None
    disk_gb: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    children: list["NormalizedDiscoveryResult"] = Field(default_factory=list)
    connections: list[NormalizedConnectionResult] = Field(default_factory=list)


class NormalizedMetricsResult(BaseModel):
    canonical_identity: str
    cpu_usage_percent: float | None = None
    ram_usage_percent: float | None = None
    disk_usage_percent: float | None = None
    network_rx_bytes: int | None = None
    network_tx_bytes: int | None = None
    timestamp: datetime = Field(default_factory=utc_now)


class BaseCollectorAdapter(ABC):
    """Abstract Base Class for all infrastructure collector adapters."""

    def __init__(self, target_host: str, target_port: int, credential_ref: str):
        self.target_host = target_host
        self.target_port = target_port
        self.credential_ref = credential_ref

    @abstractmethod
    async def discover(self) -> NormalizedDiscoveryResult:
        """Scan target to produce a normalized inventory hierarchy result."""
        pass

    @abstractmethod
    async def collect_metrics(self) -> NormalizedMetricsResult:
        """Collect current system/resource performance metrics."""
        pass

    @abstractmethod
    async def test_connection(self) -> bool:
        """Verify reachability and credential authorization without side-effects."""
        pass
