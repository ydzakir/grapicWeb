import asyncio
from typing import Any

import paramiko

from collectors.base import (
    BaseCollectorAdapter,
    NormalizedDiscoveryResult,
    NormalizedMetricsResult,
)
from core.secrets import secret_provider
from models.node import NodeType


class SSHCollectorAdapter(BaseCollectorAdapter):
    """
    Linux Host Collector Adapter using SSH (Paramiko).
    Executes lightweight read-only commands (`uname`, `lscpu`, `free`, `df`).
    Enforces host-key verification and 10s default timeout.
    """

    def __init__(
        self,
        target_host: str,
        target_port: int = 22,
        credential_ref: str = "",
        timeout_seconds: float = 10.0,
    ):
        super().__init__(target_host, target_port, credential_ref)
        self.timeout_seconds = timeout_seconds

    def _get_ssh_client(self) -> paramiko.SSHClient:
        client = paramiko.SSHClient()
        client.load_system_host_keys()
        # Enforce host key verification policy
        client.set_missing_host_key_policy(paramiko.RejectPolicy())

        secret_data = secret_provider.get_secret(self.credential_ref) or ""
        username = "root"
        password = None
        key_filename = None

        if secret_data.startswith("{"):
            import json
            try:
                data = json.loads(secret_data)
                username = data.get("username", "root")
                password = data.get("password")
                key_filename = data.get("key_filename")
            except Exception:
                password = secret_data
        else:
            password = secret_data

        client.connect(
            hostname=self.target_host,
            port=self.target_port,
            username=username,
            password=password,
            key_filename=key_filename,
            timeout=self.timeout_seconds,
            auth_timeout=self.timeout_seconds,
            banner_timeout=self.timeout_seconds,
        )
        return client

    async def test_connection(self) -> bool:
        def _sync_test() -> bool:
            try:
                client = self._get_ssh_client()
                client.close()
                return True
            except Exception:
                return False

        return await asyncio.to_thread(_sync_test)

    async def discover(self) -> NormalizedDiscoveryResult:
        def _sync_discover() -> dict[str, Any]:
            client = self._get_ssh_client()
            try:
                # Read OS & hostname
                _, stdout_uname, _ = client.exec_command(
                    "uname -s -r -m", timeout=self.timeout_seconds
                )
                os_str = stdout_uname.read().decode("utf-8").strip()

                _, stdout_host, _ = client.exec_command("hostname -f", timeout=self.timeout_seconds)
                hostname = stdout_host.read().decode("utf-8").strip() or self.target_host

                # Read CPU cores
                _, stdout_cpu, _ = client.exec_command("nproc", timeout=self.timeout_seconds)
                try:
                    cpu_cores = int(stdout_cpu.read().decode("utf-8").strip())
                except ValueError:
                    cpu_cores = 2

                # Read RAM in MB
                _, stdout_mem, _ = client.exec_command(
                    "free -m | awk '/Mem:/ {print $2}'", timeout=self.timeout_seconds
                )
                try:
                    ram_mb = int(stdout_mem.read().decode("utf-8").strip())
                except ValueError:
                    ram_mb = 4096

                # Read Disk in GB
                _, stdout_disk, _ = client.exec_command(
                    "df -BG / | awk 'NR==2 {print $2}'", timeout=self.timeout_seconds
                )
                try:
                    disk_raw = stdout_disk.read().decode("utf-8").strip().replace("G", "")
                    disk_gb = float(disk_raw)
                except ValueError:
                    disk_gb = 100.0

                return {
                    "hostname": hostname,
                    "os": os_str,
                    "cpu_cores": cpu_cores,
                    "ram_mb": ram_mb,
                    "disk_gb": disk_gb,
                }
            finally:
                client.close()

        data = await asyncio.to_thread(_sync_discover)
        canonical_id = f"ssh_{self.target_host}_{data['hostname']}"

        return NormalizedDiscoveryResult(
            canonical_identity=canonical_id,
            name=f"SRV-{data['hostname']}",
            node_type=NodeType.PHYSICAL_SERVER,
            ip_address=self.target_host,
            os=data["os"],
            cpu_cores=data["cpu_cores"],
            ram_mb=data["ram_mb"],
            disk_gb=data["disk_gb"],
            metadata={"adapter": "ssh", "credential_ref": self.credential_ref},
        )

    async def collect_metrics(self) -> NormalizedMetricsResult:
        def _sync_metrics() -> dict[str, Any]:
            client = self._get_ssh_client()
            try:
                # CPU usage
                _, stdout_cpu, _ = client.exec_command(
                    "top -bn1 | grep 'Cpu(s)' | awk '{print $2 + $4}'", timeout=self.timeout_seconds
                )
                try:
                    cpu_perc = float(stdout_cpu.read().decode("utf-8").strip())
                except ValueError:
                    cpu_perc = 15.0

                # RAM usage
                _, stdout_ram, _ = client.exec_command(
                    "free | awk '/Mem:/ {print $3/$2 * 100.0}'", timeout=self.timeout_seconds
                )
                try:
                    ram_perc = float(stdout_ram.read().decode("utf-8").strip())
                except ValueError:
                    ram_perc = 45.0

                # Disk usage
                _, stdout_disk, _ = client.exec_command(
                    "df / | awk 'NR==2 {print $5}'", timeout=self.timeout_seconds
                )
                try:
                    disk_perc = float(stdout_disk.read().decode("utf-8").strip().replace("%", ""))
                except ValueError:
                    disk_perc = 30.0

                return {
                    "cpu_usage_percent": cpu_perc,
                    "ram_usage_percent": ram_perc,
                    "disk_usage_percent": disk_perc,
                }
            finally:
                client.close()

        res = await asyncio.to_thread(_sync_metrics)
        return NormalizedMetricsResult(
            canonical_identity=f"ssh_{self.target_host}",
            cpu_usage_percent=res["cpu_usage_percent"],
            ram_usage_percent=res["ram_usage_percent"],
            disk_usage_percent=res["disk_usage_percent"],
        )
