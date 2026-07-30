import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from models.node import Node, NodeType
from services.node_service import check_hierarchy_cycle


@pytest.mark.asyncio
async def test_self_parent_cycle_defense(db_session: AsyncSession):
    node = Node(name="SelfNode", type=NodeType.PHYSICAL_SERVER)
    db_session.add(node)
    await db_session.flush()

    with pytest.raises(ValueError, match="cannot be its own parent"):
        await check_hierarchy_cycle(db_session, node.id, node.id)


@pytest.mark.asyncio
async def test_indirect_hierarchy_cycle_defense(db_session: AsyncSession):
    # Hierarchy: Root -> Host A -> VM B
    root = Node(name="Root-DC", type=NodeType.DATA_CENTER)
    db_session.add(root)
    await db_session.flush()

    host_a = Node(name="Host-A", type=NodeType.HYPERVISOR_HOST, parent_id=root.id)
    db_session.add(host_a)
    await db_session.flush()

    vm_b = Node(name="VM-B", type=NodeType.VM, parent_id=host_a.id)
    db_session.add(vm_b)
    await db_session.flush()

    # Attempting to assign VM-B as parent of Root-DC should be REJECTED
    # (Root -> Host A -> VM B -> Root)
    with pytest.raises(ValueError, match="Hierarchy cycle detected"):
        await check_hierarchy_cycle(db_session, root.id, vm_b.id)


@pytest.mark.asyncio
async def test_valid_parent_assignment(db_session: AsyncSession):
    dc = Node(name="DC2", type=NodeType.DATA_CENTER)
    host = Node(name="Host-02", type=NodeType.DOCKER_HOST)
    db_session.add_all([dc, host])
    await db_session.flush()

    # Valid parent assignment (Host-02 -> DC2) should NOT raise error
    await check_hierarchy_cycle(db_session, host.id, dc.id)
