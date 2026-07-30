import asyncio
import json
from typing import Any

import winrm

from collectors.base import (
    BaseCollectorAdapter,
    NormalizedDiscoveryResult,
    NormalizedMetricsResult,
)
from core.secrets import secret_provider
from models.node import NodeType


class WinRMCollectorAdapter(BaseCollectorAdapter):
    """
    Windows Host & Hyper-V Collector Adapter using PyWinRM.
    Executes read-only PowerShell commands for system inventory and Hyper-V VM discovery.
    Enforces certificate verification and 10s default timeout.
    """

    def __init__(
        self,
        target_host: str,
        target_port: int = 5986,
        credential_ref: str = "",
        timeout_seconds: float = 10.0,
        transport: str = "ntlm",
    ):
        super().__init__(target_host, target_port, credential_ref)
        self.timeout_seconds = timeout_seconds
        self.transport = transport

    def _get_winrm_session(self) -> winrm.Session:
        secret_data = secret_provider.get_secret(self.credential_ref) or ""
        username = "Administrator"
        password = secret_data

        if secret_data.startswith("{"):
            try:
                data = json.loads(secret_data)
                username = data.get("username", "Administrator")
                password = data.get("password", "")
            except Exception:
                password = secret_data

        endpoint = f"https://{self.target_host}:{self.target_port}/wsman"
        session = winrm.Session(
            endpoint,
            auth=(username, password),
            transport=self.transport,
            server_cert_validation="validate",  # Enforce certificate verification
            read_timeout_sec=int(self.timeout_seconds),
            operation_timeout_sec=int(self.timeout_seconds),
        )
        return session

    async def test_connection(self) -> bool:
        def _sync_test() -> bool:
            try:
                session = self._get_winrm_session()
                r = session.run_ps("Write-Output 'OK'")
                return r.status_code == 0
            except Exception:
                return False

        return await asyncio.to_thread(_sync_test)

    async def discover(self) -> NormalizedDiscoveryResult:
        def _sync_discover() -> dict[str, Any]:
            session = self._get_winrm_session()
            ps_script = """
            $os = Get-CimInstance Win32_OperatingSystem
            $cs = Get-CimInstance Win32_ComputerSystem
            $vms = @()
            if (Get-Command Get-VM -ErrorAction SilentlyContinue) {
                $vms = Get-VM | Select-Object Name, State, CPUUsage, MemoryAssigned
            }
            @{
                Hostname = $cs.DNSHostName
                OS = $os.Caption
                Cores = $cs.NumberOfLogicalProcessors
                RAM = [math]::Round($cs.TotalPhysicalMemory / 1MB)
                VMs = $vms
            } | ConvertTo-Json -Depth 3
            """
            r = session.run_ps(ps_script)
            if r.status_code != 0:
                raise RuntimeError(f"WinRM command failed: {r.std_err.decode('utf-8')}")

            return json.loads(r.std_out.decode("utf-8"))

        data = await asyncio.to_thread(_sync_discover)
        hostname = data.get("Hostname") or self.target_host
        canonical_id = f"winrm_{self.target_host}_{hostname}"

        vm_children = []
        raw_vms = data.get("VMs") or []
        if isinstance(raw_vms, dict):
            raw_vms = [raw_vms]

        for vm in raw_vms:
            vm_name = vm.get("Name", "Unknown-VM")
            vm_children.append(
                NormalizedDiscoveryResult(
                    canonical_identity=f"hyperv_vm_{self.target_host}_{vm_name}",
                    name=f"VM-{vm_name}",
                    node_type=NodeType.HYPERV_VM,
                    os="Windows / Linux VM",
                    metadata={"hypervisor": "hyperv", "state": str(vm.get("State"))},
                )
            )

        return NormalizedDiscoveryResult(
            canonical_identity=canonical_id,
            name=f"SRV-{hostname}",
            node_type=NodeType.HYPERV_HOST if vm_children else NodeType.PHYSICAL_SERVER,
            ip_address=self.target_host,
            os=data.get("OS", "Windows Server"),
            cpu_cores=data.get("Cores", 4),
            ram_mb=data.get("RAM", 8192),
            metadata={"adapter": "winrm", "credential_ref": self.credential_ref},
            children=vm_children,
        )

    async def collect_metrics(self) -> NormalizedMetricsResult:
        def _sync_metrics() -> dict[str, Any]:
            session = self._get_winrm_session()
            ps_script = """
            $cpu = (Get-CimInstance Win32_Processor |
                Measure-Object -Property LoadPercentage -Average).Average
            $os = Get-CimInstance Win32_OperatingSystem
            $ram = [math]::Round(
                ($os.TotalVisibleMemorySize - $os.FreePhysicalMemory) /
                $os.TotalVisibleMemorySize * 100, 2
            )
            @{ CPU = $cpu; RAM = $ram } | ConvertTo-Json
            """
            r = session.run_ps(ps_script)
            if r.status_code != 0:
                raise RuntimeError("WinRM metrics failed")
            return json.loads(r.std_out.decode("utf-8"))

        res = await asyncio.to_thread(_sync_metrics)
        return NormalizedMetricsResult(
            canonical_identity=f"winrm_{self.target_host}",
            cpu_usage_percent=float(res.get("CPU") or 0.0),
            ram_usage_percent=float(res.get("RAM") or 0.0),
        )
