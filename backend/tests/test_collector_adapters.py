from unittest.mock import MagicMock, patch

import pytest

from collectors.docker_collector import DockerTLSCollectorAdapter
from collectors.ssh_collector import SSHCollectorAdapter
from collectors.winrm_collector import WinRMCollectorAdapter
from models.node import NodeType


@pytest.mark.asyncio
async def test_ssh_collector_adapter_mocked():
    adapter = SSHCollectorAdapter(target_host="192.168.1.50", target_port=22)

    mock_client = MagicMock()
    mock_uname = MagicMock()
    mock_uname.read.return_value = b"Linux 5.15.0 x86_64"
    mock_host = MagicMock()
    mock_host.read.return_value = b"srv-web-01"
    mock_cpu = MagicMock()
    mock_cpu.read.return_value = b"8"
    mock_mem = MagicMock()
    mock_mem.read.return_value = b"16384"
    mock_disk = MagicMock()
    mock_disk.read.return_value = b"250G"

    mock_client.exec_command.side_effect = [
        (None, mock_uname, None),
        (None, mock_host, None),
        (None, mock_cpu, None),
        (None, mock_mem, None),
        (None, mock_disk, None),
    ]

    with patch.object(adapter, "_get_ssh_client", return_value=mock_client):
        result = await adapter.discover()
        assert result.canonical_identity == "ssh_192.168.1.50_srv-web-01"
        assert result.name == "SRV-srv-web-01"
        assert result.node_type == NodeType.PHYSICAL_SERVER
        assert result.cpu_cores == 8
        assert result.ram_mb == 16384


@pytest.mark.asyncio
async def test_winrm_collector_adapter_mocked():
    adapter = WinRMCollectorAdapter(target_host="192.168.1.60", target_port=5986)

    mock_session = MagicMock()
    mock_response = MagicMock()
    mock_response.status_code = 0
    mock_response.std_out = (
        b'{"Hostname": "WIN-HYPERV-01", "OS": "Windows Server 2022", '
        b'"Cores": 16, "RAM": 32768, "VMs": [{"Name": "VM-APP-01", "State": "Running"}]}'
    )
    mock_session.run_ps.return_value = mock_response

    with patch.object(adapter, "_get_winrm_session", return_value=mock_session):
        result = await adapter.discover()
        assert result.canonical_identity == "winrm_192.168.1.60_WIN-HYPERV-01"
        assert result.node_type == NodeType.HYPERV_HOST
        assert len(result.children) == 1
        assert result.children[0].node_type == NodeType.HYPERV_VM
        assert result.children[0].name == "VM-VM-APP-01"


@pytest.mark.asyncio
async def test_docker_tls_prohibits_unencrypted_remote_port():
    # Attempting unencrypted remote port 2375 in production must raise Security Policy Violation
    adapter = DockerTLSCollectorAdapter(
        target_host="remote-docker-host.com",
        target_port=2375,
        is_production=True,
    )

    with pytest.raises(ValueError, match="Unencrypted remote Docker port 2375 is prohibited"):
        await adapter.discover()
