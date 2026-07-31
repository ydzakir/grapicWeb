import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.audit import AuditLog
from models.node import LifecycleStatus, Node, NodeStatus, NodeType, ReviewStatus
from models.user import User
from services.node_service import is_host_type


async def create_datacenter(
    db: AsyncSession,
    name: str,
    location: str | None = None,
    metadata: dict[str, Any] | None = None,
    admin_user: User | None = None,
) -> Node:
    """
    Create a new Data Center node (Admin only).
    Data Centers act as top-level grouping roots for approved host nodes.
    """
    meta = metadata.copy() if metadata else {}
    if location:
        meta["location"] = location

    dc_node = Node(
        name=name,
        type=NodeType.DATA_CENTER,
        status=NodeStatus.UP,
        review_status=ReviewStatus.APPROVED,  # Data Centers created by admin are auto-approved
        lifecycle_status=LifecycleStatus.ACTIVE,
        metadata_=meta,
    )
    db.add(dc_node)
    await db.flush()

    if admin_user:
        audit_entry = AuditLog(
            actor_username=admin_user.username,
            action="datacenter.created",
            target=f"Node:{dc_node.id}",
            metadata_={"datacenter_id": str(dc_node.id), "name": name, "location": location},
        )
        db.add(audit_entry)
        await db.flush()

    return dc_node


async def get_datacenters(db: AsyncSession) -> list[Node]:
    """
    Get all active Data Center nodes.
    """
    stmt = (
        select(Node)
        .where(
            Node.type == NodeType.DATA_CENTER,
            Node.lifecycle_status == LifecycleStatus.ACTIVE,
        )
        .order_by(Node.name.asc())
    )
    res = await db.execute(stmt)
    return list(res.scalars().all())


async def update_datacenter(
    db: AsyncSession,
    datacenter_id: uuid.UUID,
    name: str | None = None,
    location: str | None = None,
    metadata: dict[str, Any] | None = None,
    admin_user: User | None = None,
) -> Node:
    dc_node = await db.get(Node, datacenter_id)
    if not dc_node or dc_node.type != NodeType.DATA_CENTER:
        raise ValueError(f"Data Center '{datacenter_id}' not found.")

    if name:
        dc_node.name = name

    meta = dc_node.metadata_.copy() if dc_node.metadata_ else {}
    if location is not None:
        meta["location"] = location
    if metadata:
        meta.update(metadata)

    dc_node.metadata_ = meta
    await db.flush()

    if admin_user:
        audit_entry = AuditLog(
            actor_username=admin_user.username,
            action="datacenter.updated",
            target=f"Node:{dc_node.id}",
            metadata_={"datacenter_id": str(dc_node.id), "name": dc_node.name},
        )
        db.add(audit_entry)
        await db.flush()

    return dc_node


async def delete_datacenter(
    db: AsyncSession,
    datacenter_id: uuid.UUID,
    admin_user: User | None = None,
) -> None:
    dc_node = await db.get(Node, datacenter_id)
    if not dc_node or dc_node.type != NodeType.DATA_CENTER:
        raise ValueError(f"Data Center '{datacenter_id}' not found.")

    # Unassign assigned child hosts before soft archiving/deleting DC node
    stmt = select(Node).where(Node.parent_id == datacenter_id)
    res = await db.execute(stmt)
    children = res.scalars().all()
    for child in children:
        child.parent_id = None

    dc_node.lifecycle_status = LifecycleStatus.ARCHIVED
    await db.flush()

    if admin_user:
        audit_entry = AuditLog(
            actor_username=admin_user.username,
            action="datacenter.deleted",
            target=f"Node:{dc_node.id}",
            metadata_={"datacenter_id": str(dc_node.id), "name": dc_node.name},
        )
        db.add(audit_entry)
        await db.flush()


async def assign_hosts_to_datacenter(
    db: AsyncSession,
    datacenter_id: uuid.UUID,
    host_ids: list[uuid.UUID],
    admin_user: User,
) -> list[Node]:
    """
    Assign a list of approved host nodes to a Data Center.
    """
    dc_node = await db.get(Node, datacenter_id)
    if not dc_node or dc_node.type != NodeType.DATA_CENTER:
        raise ValueError(f"Data Center '{datacenter_id}' not found.")

    assigned_hosts: list[Node] = []
    for host_id in host_ids:
        host_node = await db.get(Node, host_id)
        if not host_node:
            raise ValueError(f"Host '{host_id}' not found.")
        if not is_host_type(host_node.type):
            raise ValueError(f"Node '{host_node.name}' is not a valid host node.")

        host_node.parent_id = datacenter_id
        assigned_hosts.append(host_node)

    await db.flush()

    audit_entry = AuditLog(
        actor_username=admin_user.username,
        action="datacenter.hosts_assigned",
        target=f"Node:{datacenter_id}",
        metadata_={
            "datacenter_id": str(datacenter_id),
            "host_ids": [str(hid) for hid in host_ids],
        },
    )
    db.add(audit_entry)
    await db.flush()

    return assigned_hosts
