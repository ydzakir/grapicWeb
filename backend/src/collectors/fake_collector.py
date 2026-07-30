
from collectors.base import (
    BaseCollectorAdapter,
    NormalizedDiscoveryResult,
    NormalizedMetricsResult,
)
from models.node import NodeType


class FakeCollectorAdapter(BaseCollectorAdapter):
    """
    Deterministic fake collector adapter for offline testing, CI/CD, and demo.
    Generates predictable host, Hyper-V VM, and Docker container hierarchies.
    """

    def __init__(
        self,
        target_host: str = "fake-host-01.local",
        target_port: int = 22,
        credential_ref: str = "fake_cred_ref",
        simulate_failure_mode: str | None = None,
    ):
        super().__init__(target_host, target_port, credential_ref)
        self.simulate_failure_mode = simulate_failure_mode

    async def test_connection(self) -> bool:
        if self.simulate_failure_mode == "auth_error":
            return False
        if self.simulate_failure_mode in ("timeout", "connection_refused"):
            raise TimeoutError("Fake connection timeout")
        return True

    async def discover(self) -> NormalizedDiscoveryResult:
        if self.simulate_failure_mode == "timeout":
            raise TimeoutError("Fake discovery timeout")
        if self.simulate_failure_mode == "connection_refused":
            raise ConnectionRefusedError("Fake connection refused")

        canonical_id = f"fake_host_{self.target_host}"
        return NormalizedDiscoveryResult(
            canonical_identity=canonical_id,
            name=f"SRV-{self.target_host}",
            node_type=NodeType.PHYSICAL_SERVER,
            ip_address=(
                self.target_host
                if not self.target_host.endswith(".local")
                else "192.168.1.100"
            ),
            os="Ubuntu 24.04 LTS",
            cpu_cores=16,
            ram_mb=32768,
            disk_gb=500.0,
            metadata={"collector_type": "fake", "capability": ["hyperv", "docker"]},
            children=[
                NormalizedDiscoveryResult(
                    canonical_identity=f"fake_vm_{self.target_host}_vm1",
                    name=f"VM-{self.target_host}-WEB",
                    node_type=NodeType.HYPERV_VM,
                    ip_address="10.0.0.15",
                    os="Windows Server 2022",
                    cpu_cores=4,
                    ram_mb=8192,
                    disk_gb=100.0,
                    metadata={"hypervisor": "hyperv"},
                ),
                NormalizedDiscoveryResult(
                    canonical_identity=f"fake_container_{self.target_host}_nginx",
                    name=f"{self.target_host}/nginx-proxy",
                    node_type=NodeType.DOCKER_CONTAINER,
                    ip_address="172.18.0.2",
                    os="Linux",
                    cpu_cores=2,
                    ram_mb=1024,
                    disk_gb=10.0,
                    metadata={"container_id": "c1234567890a", "image": "nginx:alpine"},
                ),
            ],
        )

    async def collect_metrics(self) -> NormalizedMetricsResult:
        if self.simulate_failure_mode == "timeout":
            raise TimeoutError("Fake metrics collection timeout")
        if self.simulate_failure_mode == "connection_refused":
            raise ConnectionRefusedError("Fake connection refused")

        return NormalizedMetricsResult(
            canonical_identity=f"fake_host_{self.target_host}",
            cpu_usage_percent=35.5,
            ram_usage_percent=62.0,
            disk_usage_percent=45.2,
            network_rx_bytes=10485760,
            network_tx_bytes=5242880,
        )
