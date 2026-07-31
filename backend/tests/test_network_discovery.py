import pytest
from models.node import Node, NodeStatus
from models.network import EdgeConfidenceLevel
from services.network_discovery_service import (
    parse_arp_table_output,
    discover_snmp_interfaces,
    create_manual_network_edge,
)


def test_parse_arp_table_output():
    raw_arp = """
    Interface: 192.168.1.1 --- 0x3
      Internet Address      Physical Address      Type
      192.168.1.100         00-15-5d-01-02-03     dynamic
      192.168.1.101         00-15-5d-04-05-06     dynamic
    """
    entries = parse_arp_table_output(raw_arp)
    assert len(entries) == 2
    assert entries[0] == ("192.168.1.100", "00-15-5d-01-02-03")
    assert entries[1] == ("192.168.1.101", "00-15-5d-04-05-06")


@pytest.mark.asyncio
async def test_snmp_interface_discovery():
    ifaces = await discover_snmp_interfaces("192.168.1.50")
    assert len(ifaces) >= 2
    assert ifaces[0]["if_name"] == "eth0"


@pytest.mark.asyncio
async def test_create_manual_network_edge_with_audit_trail(db_session):
    node1 = Node(name="NODE-DISCOVERY-01", type="physical_server", status=NodeStatus.UP, review_status="approved", lifecycle_status="active")
    node2 = Node(name="NODE-DISCOVERY-02", type="physical_server", status=NodeStatus.UP, review_status="approved", lifecycle_status="active")
    db_session.add_all([node1, node2])
    await db_session.commit()

    edge = await create_manual_network_edge(
        db=db_session,
        source_node_id=node1.id,
        target_node_id=node2.id,
        connection_type="manual_uplink",
        username="net_admin",
    )

    assert edge.source_node_id == node1.id
    assert edge.target_node_id == node2.id
    assert edge.confidence_level == EdgeConfidenceLevel.MANUAL
    assert edge.provenance == "manual_user_defined"
