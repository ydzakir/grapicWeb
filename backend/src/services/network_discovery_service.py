import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from models.network import NetworkEdge, EdgeConfidenceLevel, Subnet
from models.node import Node
from models.audit import AuditLog


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def parse_arp_table_output(raw_output: str) -> List[Tuple[str, str]]:
    """
    Parses ARP table output string into (ip_address, mac_address) tuples.
    Format example: "192.168.1.100  00-15-5d-01-02-03  dynamic"
    """
    entries = []
    lines = raw_output.strip().splitlines()
    ip_mac_pattern = re.compile(
        r"(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\s+([0-9a-fa-f]{2}[:-][0-9a-fa-f]{2}[:-][0-9a-fa-f]{2}[:-][0-9a-fa-f]{2}[:-][0-9a-fa-f]{2}[:-][0-9a-fa-f]{2})"
    )
    for line in lines:
        match = ip_mac_pattern.search(line)
        if match:
            entries.append((match.group(1), match.group(2).lower()))
    return entries


async def discover_snmp_interfaces(host_or_ip: str) -> List[Dict[str, Any]]:
    """
    Simulates / extracts SNMP interface table data.
    """
    return [
        {"if_index": 1, "if_name": "eth0", "ip": host_or_ip, "speed_mbps": 1000, "status": "up"},
        {"if_index": 2, "if_name": "eth1", "ip": "10.0.1.1", "speed_mbps": 10000, "status": "up"},
    ]


async def create_manual_network_edge(
    db: AsyncSession,
    source_node_id: uuid.UUID,
    target_node_id: uuid.UUID,
    connection_type: str = "manual_link",
    username: str = "admin",
) -> NetworkEdge:
    """
    Creates a manual network mapping fallback edge with audit log tracking.
    """
    now = utc_now()
    
    # Check if edge already exists
    stmt = select(NetworkEdge).where(
        and_(
            NetworkEdge.source_node_id == source_node_id,
            NetworkEdge.target_node_id == target_node_id,
        )
    )
    res = await db.execute(stmt)
    existing_edge = res.scalars().first()

    if existing_edge:
        existing_edge.connection_type = connection_type
        existing_edge.provenance = "manual_user_defined"
        existing_edge.confidence_level = EdgeConfidenceLevel.MANUAL
        existing_edge.last_verified_at = now
        edge = existing_edge
    else:
        edge = NetworkEdge(
            source_node_id=source_node_id,
            target_node_id=target_node_id,
            connection_type=connection_type,
            provenance="manual_user_defined",
            confidence_level=EdgeConfidenceLevel.MANUAL,
            has_active_traffic=True,
            last_verified_at=now,
        )
        db.add(edge)

    # Log audit entry
    audit = AuditLog(
        actor_username=username,
        action="CREATE_MANUAL_NETWORK_EDGE",
        target=f"{source_node_id}->{target_node_id}",
        metadata_={"connection_type": connection_type, "provenance": "manual_user_defined"},
    )
    db.add(audit)
    await db.commit()
    await db.refresh(edge)
    return edge


import asyncio
import ipaddress
from models.node import NodeType, NodeStatus, ReviewStatus, LifecycleStatus
from services.node_service import upsert_inventory_node


async def probe_ip_host(ip_str: str) -> dict[str, Any] | None:
    """Probe an IP address across standard infrastructure service ports concurrently."""
    common_ports = [
        (22, "ssh", "Linux Server", "physical_server", "Linux"),
        (5986, "winrm_https", "Windows Hyper-V Host", "hyperv_host", "Windows Server"),
        (5985, "winrm_http", "Windows Server", "hyperv_host", "Windows Server"),
        (2376, "docker_tls", "Docker Host", "docker_host", "Linux/Docker"),
        (2375, "docker_tcp", "Docker Host", "docker_host", "Linux/Docker"),
        (3389, "rdp", "Windows Server", "physical_server", "Windows Server"),
        (443, "https", "Web Service/API Node", "service", "Linux"),
        (80, "http", "Web Service Node", "service", "Linux"),
    ]

    for port, proto, desc, node_type, os_hint in common_ports:
        try:
            _, writer = await asyncio.wait_for(
                asyncio.open_connection(ip_str, port), timeout=0.35
            )
            writer.close()
            await writer.wait_closed()
            # Host responded on this port!
            ip_suffix = ip_str.split(".")[-1]
            suggested_name = f"{node_type.upper().replace('_', '-')}-AUTO-{ip_suffix}"
            return {
                "ip_address": ip_str,
                "port": port,
                "protocol": proto,
                "suggested_name": suggested_name,
                "node_type": node_type,
                "os": os_hint,
                "status": "up",
            }
        except (OSError, asyncio.TimeoutError):
            continue

    return None


async def scan_subnet_ip_range(
    db: AsyncSession,
    cidr: str,
    username: str = "admin",
) -> dict[str, Any]:
    """
    Scans a CIDR subnet (e.g. 10.10.0.0/24) for active IP hosts and automatically registers discovered nodes into Inventory.
    """
    try:
        network = ipaddress.ip_network(cidr.strip(), strict=False)
    except ValueError as e:
        raise ValueError(f"Invalid CIDR subnet format '{cidr}': {str(e)}")

    hosts = list(network.hosts())
    # Limit max hosts per scan request to 256 for optimal performance
    if len(hosts) > 512:
        hosts = hosts[:512]

    tasks = [probe_ip_host(str(h)) for h in hosts]
    results = await asyncio.gather(*tasks)

    discovered = [r for r in results if r is not None]
    added_nodes = []

    for d in discovered:
        node = await upsert_inventory_node(
            db=db,
            name=d["suggested_name"],
            node_type=NodeType(d["node_type"]),
            os=d["os"],
            ip_address=d["ip_address"],
            status=NodeStatus.UP,
            metadata={"discovery_source": "subnet_cidr_auto_scan", "discovered_port": d["port"], "scanned_cidr": cidr},
        )
        added_nodes.append({
            "id": str(node.id),
            "name": node.name,
            "ip_address": node.ip_address,
            "type": node.type,
            "os": node.os,
            "status": node.status,
            "review_status": node.review_status,
        })

    # Log audit entry
    audit = AuditLog(
        actor_username=username,
        action="SUBNET_CIDR_AUTO_SCAN",
        target=cidr,
        metadata_={"scanned_hosts": len(hosts), "discovered_count": len(discovered)},
    )
    db.add(audit)
    await db.commit()

    return {
        "cidr": cidr,
        "scanned_hosts_count": len(hosts),
        "discovered_count": len(discovered),
        "items": added_nodes,
    }
