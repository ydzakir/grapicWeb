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
