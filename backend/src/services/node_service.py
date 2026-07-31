import re
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.audit import AuditLog
from models.node import LifecycleStatus, Node, NodeStatus, NodeType, ReviewStatus
from models.user import User

# Host naming pattern: [TYPE]-[LOKASI]-[FUNGSI]-[NOMOR]
HOST_NAMING_PATTERN = re.compile(r"^[A-Z0-9]+-[A-Z0-9]+-[A-Z0-9]+-\d+$")


def validate_host_naming_convention(name: str) -> tuple[bool, str | None]:
    """
    Validate host naming convention: [TYPE]-[LOKASI]-[FUNGSI]-[NOMOR]
    Example: HYPERV-DC1-WEB-01, DOCKER-DC1-APP-02, PHYSICAL-DC2-DB-01
    """
    if not name:
        return False, "Node name cannot be empty."

    cleaned_name = name.strip()
    if not HOST_NAMING_PATTERN.match(cleaned_name):
        return (
            False,
            f"Host name '{name}' does not follow convention '[TYPE]-[LOKASI]-[FUNGSI]-[NOMOR]' (e.g. HYPERV-DC1-WEB-01).",
        )

    return True, None


HOST_NODE_TYPES = [
    NodeType.PHYSICAL_SERVER,
    NodeType.HYPERV_HOST,
    NodeType.HYPERVISOR_HOST,
    NodeType.DOCKER_HOST,
]


def is_host_type(node_type: NodeType) -> bool:
    return node_type in HOST_NODE_TYPES


async def check_hierarchy_cycle(
    db: AsyncSession, node_id: uuid.UUID, proposed_parent_id: uuid.UUID | None
) -> None:
    """
    Check if assigning proposed_parent_id to node_id would create a hierarchy cycle.
    Raises ValueError if a cycle is detected.
    """
    if proposed_parent_id is None:
        return

    if node_id == proposed_parent_id:
        raise ValueError("Hierarchy cycle detected: A node cannot be its own parent.")

    current_id: uuid.UUID | None = proposed_parent_id
    visited: set[uuid.UUID] = {node_id}

    while current_id is not None:
        if current_id in visited:
            raise ValueError(
                f"Hierarchy cycle detected: Node '{node_id}' "
                f"is an ancestor of proposed parent '{proposed_parent_id}'."
            )
        visited.add(current_id)

        stmt = select(Node.parent_id).where(Node.id == current_id)
        result = await db.execute(stmt)
        current_id = result.scalars().first()


async def find_existing_host_node(
    db: AsyncSession,
    ip_address: str | None,
    name: str,
    machine_id: str | None = None,
) -> Node | None:
    """
    Find canonical host node by machine_id, ip_address, or exact name match among host types.
    """
    stmt = select(Node).where(Node.type.in_(HOST_NODE_TYPES))
    res = await db.execute(stmt)
    hosts = list(res.scalars().all())

    if machine_id:
        for host in hosts:
            if host.metadata_ and host.metadata_.get("machine_id") == machine_id:
                return host

    if ip_address:
        for host in hosts:
            if host.ip_address == ip_address:
                return host

    for host in hosts:
        if host.name == name:
            return host

    return None


async def upsert_inventory_node(
    db: AsyncSession,
    name: str,
    node_type: NodeType,
    parent_id: uuid.UUID | None = None,
    os: str | None = None,
    cpu_cores: int | None = None,
    ram_mb: int | None = None,
    disk_gb: float | None = None,
    ip_address: str | None = None,
    status: NodeStatus = NodeStatus.UP,
    metadata: dict[str, Any] | None = None,
) -> Node:
    """
    Normalized, idempotent upsert of discovery results.
    - Preserves single canonical host node per physical/hypervisor/docker host machine.
    - Formats container display name as `<docker-host>/<container-name>`.
    - Preserves raw container name in metadata.
    - Marks new discovery review_status = PENDING and attaches validation issue if host name invalid.
    - Idempotently updates last_seen, status, and system metrics.
    """
    meta = metadata.copy() if metadata else {}
    now = datetime.now(timezone.utc)

    # If this is a container, format display name and link canonical docker host parent
    if node_type in (NodeType.DOCKER_CONTAINER, NodeType.CONTAINER):
        meta["container_name"] = name
        container_raw_name = name.lstrip("/")
        docker_host_name = meta.get("docker_host_name")

        if parent_id:
            parent_node = await db.get(Node, parent_id)
            if parent_node:
                docker_host_name = parent_node.name

        if docker_host_name:
            display_name = f"{docker_host_name}/{container_raw_name}"
        else:
            display_name = container_raw_name

        stmt = select(Node).where(
            Node.type.in_([NodeType.DOCKER_CONTAINER, NodeType.CONTAINER])
        )
        res = await db.execute(stmt)
        containers = list(res.scalars().all())
        existing_container = None
        for c in containers:
            if c.name == display_name or (
                c.parent_id == parent_id
                and c.metadata_
                and c.metadata_.get("container_name") == name
            ):
                existing_container = c
                break

        if existing_container:
            existing_container.name = display_name
            existing_container.status = status
            existing_container.last_seen = now
            if os is not None:
                existing_container.os = os
            if cpu_cores is not None:
                existing_container.cpu_cores = cpu_cores
            if ram_mb is not None:
                existing_container.ram_mb = ram_mb
            if disk_gb is not None:
                existing_container.disk_gb = disk_gb
            if ip_address is not None:
                existing_container.ip_address = ip_address

            merged_meta = existing_container.metadata_.copy() if existing_container.metadata_ else {}
            merged_meta.update(meta)
            existing_container.metadata_ = merged_meta

            await db.flush()
            return existing_container
        else:
            new_container = Node(
                name=display_name,
                type=NodeType.DOCKER_CONTAINER,
                parent_id=parent_id,
                os=os,
                cpu_cores=cpu_cores,
                ram_mb=ram_mb,
                disk_gb=disk_gb,
                ip_address=ip_address,
                status=status,
                review_status=ReviewStatus.PENDING,
                lifecycle_status=LifecycleStatus.ACTIVE,
                last_seen=now,
                metadata_=meta,
            )
            db.add(new_container)
            await db.flush()
            return new_container

    # Host node or VM discovery
    if is_host_type(node_type):
        machine_id = meta.get("machine_id")
        existing_host = await find_existing_host_node(
            db=db, ip_address=ip_address, name=name, machine_id=machine_id
        )

        # Validate host naming convention
        is_valid_name, val_err = validate_host_naming_convention(name)
        if not is_valid_name:
            meta["validation_issue"] = val_err

        if existing_host:
            # Upgrade node type to more specific capability if applicable
            if node_type == NodeType.HYPERV_HOST:
                existing_host.type = NodeType.HYPERV_HOST
            elif node_type == NodeType.DOCKER_HOST and existing_host.type != NodeType.HYPERV_HOST:
                existing_host.type = NodeType.DOCKER_HOST

            existing_host.status = status
            existing_host.last_seen = now
            if os is not None:
                existing_host.os = os
            if cpu_cores is not None:
                existing_host.cpu_cores = cpu_cores
            if ram_mb is not None:
                existing_host.ram_mb = ram_mb
            if disk_gb is not None:
                existing_host.disk_gb = disk_gb
            if ip_address is not None:
                existing_host.ip_address = ip_address
            if parent_id is not None:
                await check_hierarchy_cycle(db, existing_host.id, parent_id)
                existing_host.parent_id = parent_id

            merged_meta = existing_host.metadata_.copy() if existing_host.metadata_ else {}
            merged_meta.update(meta)
            existing_host.metadata_ = merged_meta

            await db.flush()
            return existing_host
        else:
            new_host = Node(
                name=name,
                type=node_type,
                parent_id=parent_id,
                os=os,
                cpu_cores=cpu_cores,
                ram_mb=ram_mb,
                disk_gb=disk_gb,
                ip_address=ip_address,
                status=status,
                review_status=ReviewStatus.PENDING,
                lifecycle_status=LifecycleStatus.ACTIVE,
                last_seen=now,
                metadata_=meta,
            )
            db.add(new_host)
            await db.flush()
            return new_host

    # VM discovery (e.g. HYPERV_VM)
    stmt = select(Node).where(
        Node.type.in_([NodeType.HYPERV_VM, NodeType.VM]),
        or_(
            Node.name == name,
            (Node.parent_id == parent_id) & (Node.name == name),
        ),
    )
    res = await db.execute(stmt)
    existing_vm = res.scalars().first()

    if existing_vm:
        existing_vm.status = status
        existing_vm.last_seen = now
        if os is not None:
            existing_vm.os = os
        if cpu_cores is not None:
            existing_vm.cpu_cores = cpu_cores
        if ram_mb is not None:
            existing_vm.ram_mb = ram_mb
        if disk_gb is not None:
            existing_vm.disk_gb = disk_gb
        if ip_address is not None:
            existing_vm.ip_address = ip_address
        if parent_id is not None:
            await check_hierarchy_cycle(db, existing_vm.id, parent_id)
            existing_vm.parent_id = parent_id

        merged_meta = existing_vm.metadata_.copy() if existing_vm.metadata_ else {}
        merged_meta.update(meta)
        existing_vm.metadata_ = merged_meta

        await db.flush()
        return existing_vm
    else:
        new_vm = Node(
            name=name,
            type=NodeType.HYPERV_VM,
            parent_id=parent_id,
            os=os,
            cpu_cores=cpu_cores,
            ram_mb=ram_mb,
            disk_gb=disk_gb,
            ip_address=ip_address,
            status=status,
            review_status=ReviewStatus.PENDING,
            lifecycle_status=LifecycleStatus.ACTIVE,
            last_seen=now,
            metadata_=meta,
        )
        db.add(new_vm)
        await db.flush()
        return new_vm


async def approve_node(
    db: AsyncSession,
    node_id: uuid.UUID,
    admin_user: User,
    new_name: str | None = None,
) -> Node:
    """
    Approve a pending node.
    Enforces host naming convention rule. Raises ValueError if host name is invalid.
    Logs audit event.
    """
    node = await db.get(Node, node_id)
    if not node:
        raise ValueError(f"Node '{node_id}' not found.")

    target_name = new_name.strip() if new_name else node.name

    # Validate host naming convention if it's a host node
    if is_host_type(node.type):
        is_valid, val_err = validate_host_naming_convention(target_name)
        if not is_valid:
            raise ValueError(f"Cannot approve node: {val_err}")

    if new_name:
        node.name = target_name

    # Clear validation issue if any
    meta = node.metadata_.copy() if node.metadata_ else {}
    meta.pop("validation_issue", None)
    node.metadata_ = meta

    node.review_status = ReviewStatus.APPROVED

    # Audit log
    audit_entry = AuditLog(
        actor_username=admin_user.username,
        action="node.approved",
        target=f"Node:{node.id}",
        metadata_={"node_id": str(node.id), "node_name": node.name, "type": str(node.type)},
    )
    db.add(audit_entry)
    await db.flush()

    return node


async def reject_node(
    db: AsyncSession,
    node_id: uuid.UUID,
    admin_user: User,
    reason: str | None = None,
) -> Node:
    """
    Reject a pending node.
    Logs audit event.
    """
    node = await db.get(Node, node_id)
    if not node:
        raise ValueError(f"Node '{node_id}' not found.")

    node.review_status = ReviewStatus.REJECTED

    meta = node.metadata_.copy() if node.metadata_ else {}
    if reason:
        meta["rejection_reason"] = reason
    node.metadata_ = meta

    audit_entry = AuditLog(
        actor_username=admin_user.username,
        action="node.rejected",
        target=f"Node:{node.id}",
        metadata_={"node_id": str(node.id), "node_name": node.name, "reason": reason},
    )
    db.add(audit_entry)
    await db.flush()

    return node


async def archive_node(
    db: AsyncSession,
    node_id: uuid.UUID,
    admin_user: User,
) -> Node:
    """
    Archive a node (soft deletion retention lifecycle).
    Logs audit event.
    """
    node = await db.get(Node, node_id)
    if not node:
        raise ValueError(f"Node '{node_id}' not found.")

    node.lifecycle_status = LifecycleStatus.ARCHIVED

    audit_entry = AuditLog(
        actor_username=admin_user.username,
        action="node.archived",
        target=f"Node:{node.id}",
        metadata_={"node_id": str(node.id), "node_name": node.name},
    )
    db.add(audit_entry)
    await db.flush()

    return node


async def get_nodes_paginated(
    db: AsyncSession,
    page: int = 1,
    page_size: int = 20,
    search: str | None = None,
    node_type: NodeType | None = None,
    status: NodeStatus | None = None,
    review_status: ReviewStatus | None = None,
    lifecycle_status: LifecycleStatus | None = None,
) -> tuple[int, list[Node]]:
    """
    Get paginated nodes with flexible search and status/type filters.
    """
    query = select(Node)

    if search:
        search_pattern = f"%{search.strip()}%"
        query = query.where(
            or_(
                Node.name.ilike(search_pattern),
                Node.ip_address.ilike(search_pattern),
                Node.os.ilike(search_pattern),
            )
        )

    if node_type:
        query = query.where(Node.type == node_type)

    if status:
        query = query.where(Node.status == status)

    if review_status:
        query = query.where(Node.review_status == review_status)

    if lifecycle_status:
        query = query.where(Node.lifecycle_status == lifecycle_status)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_res = await db.execute(count_query)
    total = total_res.scalar() or 0

    # Paginate
    offset = (page - 1) * page_size
    query = query.order_by(Node.created_at.desc()).offset(offset).limit(page_size)
    res = await db.execute(query)
    items = list(res.scalars().all())

    return total, items
