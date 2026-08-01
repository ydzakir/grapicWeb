from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from collectors.base import NormalizedDiscoveryResult
from models.node import LifecycleStatus, Node, NodeStatus, ReviewStatus


def utc_now() -> datetime:
    return datetime.now(UTC)


async def process_collector_success(
    db: AsyncSession,
    canonical_identity: str,
) -> Node | None:
    """
    Process successful poll for a node:
    - Update last_seen to now
    - Set status to UP
    - Reset failure state tracking
    """
    stmt = select(Node).where(
        Node.metadata_["canonical_identity"].as_string() == canonical_identity
    )
    result = await db.execute(stmt)
    node = result.scalars().first()

    if not node:
        # Check by external_id in metadata
        stmt_ext = select(Node).where(
            Node.metadata_["external_id"].as_string() == canonical_identity
        )
        res_ext = await db.execute(stmt_ext)
        node = res_ext.scalars().first()

    if node:
        meta = dict(node.metadata_ or {})
        meta["first_failed_at"] = None
        meta["consecutive_failures"] = 0
        node.metadata_ = meta
        node.status = NodeStatus.UP
        node.last_seen = utc_now()
        await db.commit()
        await db.refresh(node)

        if node.review_status == ReviewStatus.APPROVED and node.lifecycle_status == LifecycleStatus.ACTIVE:
            try:
                from services.status_broadcaster import broadcast_node_status_change
                await broadcast_node_status_change(
                    node_id=str(node.id),
                    name=node.name,
                    node_type=node.type.value if hasattr(node.type, "value") else str(node.type),
                    status=node.status.value if hasattr(node.status, "value") else str(node.status),
                    last_seen=node.last_seen.isoformat() if node.last_seen else None,
                )
            except Exception:
                pass

    return node


async def process_collector_failure(
    db: AsyncSession,
    canonical_identity: str,
    error_message: str,
) -> Node | None:
    """
    Process poll failure / timeout for a node according to status transition rules:
    - 1st failure -> status UNKNOWN, set first_failed_at timestamp
    - Consecutive failure window > 120 seconds (2 minutes) -> status DOWN
    """
    now = utc_now()
    stmt = select(Node).where(
        Node.metadata_["canonical_identity"].as_string() == canonical_identity
    )
    result = await db.execute(stmt)
    node = result.scalars().first()

    if not node:
        stmt_ext = select(Node).where(
            Node.metadata_["external_id"].as_string() == canonical_identity
        )
        res_ext = await db.execute(stmt_ext)
        node = res_ext.scalars().first()

    if node:
        meta = dict(node.metadata_ or {})
        first_failed_at_str = meta.get("first_failed_at")
        consecutive_failures = int(meta.get("consecutive_failures") or 0) + 1

        if not first_failed_at_str:
            first_failed_at = now
            meta["first_failed_at"] = now.isoformat()
        else:
            try:
                first_failed_at = datetime.fromisoformat(first_failed_at_str)
                if first_failed_at.tzinfo is None:
                    first_failed_at = first_failed_at.replace(tzinfo=UTC)
            except Exception:
                first_failed_at = now
                meta["first_failed_at"] = now.isoformat()

        meta["consecutive_failures"] = consecutive_failures
        meta["last_error"] = error_message
        node.metadata_ = meta

        failure_window_seconds = (now - first_failed_at).total_seconds()
        if failure_window_seconds > 120.0:
            node.status = NodeStatus.DOWN
        else:
            node.status = NodeStatus.UNKNOWN

        await db.commit()
        await db.refresh(node)

        if node.review_status == ReviewStatus.APPROVED and node.lifecycle_status == LifecycleStatus.ACTIVE:
            try:
                from services.status_broadcaster import broadcast_node_status_change
                await broadcast_node_status_change(
                    node_id=str(node.id),
                    name=node.name,
                    node_type=node.type.value if hasattr(node.type, "value") else str(node.type),
                    status=node.status.value if hasattr(node.status, "value") else str(node.status),
                    last_seen=node.last_seen.isoformat() if node.last_seen else None,
                )
            except Exception:
                pass

    return node


async def process_discovery_result(
    db: AsyncSession,
    discovery: NormalizedDiscoveryResult,
    parent_id: Any | None = None,
) -> Node:
    """
    Upsert discovered node into inventory:
    - New discovered nodes get review_status = PENDING
    - Idempotent scan by canonical_identity
    """
    stmt = select(Node).where(
        Node.metadata_["canonical_identity"].as_string() == discovery.canonical_identity
    )
    result = await db.execute(stmt)
    node = result.scalars().first()

    now = utc_now()
    if not node:
        # Create new discovered node with review_status PENDING
        meta = {
            "canonical_identity": discovery.canonical_identity,
            "external_id": discovery.canonical_identity,
            **discovery.metadata,
        }
        node = Node(
            name=discovery.name,
            type=discovery.node_type,
            parent_id=parent_id,
            os=discovery.os,
            cpu_cores=discovery.cpu_cores,
            ram_mb=discovery.ram_mb,
            disk_gb=discovery.disk_gb,
            ip_address=discovery.ip_address,
            status=NodeStatus.UP,
            review_status=ReviewStatus.PENDING,  # Discovered new node is PENDING review
            lifecycle_status=LifecycleStatus.ACTIVE,
            last_seen=now,
            metadata_=meta,
        )
        db.add(node)
        await db.flush()
    else:
        # Update existing node
        node.name = discovery.name
        node.os = discovery.os or node.os
        node.cpu_cores = discovery.cpu_cores or node.cpu_cores
        node.ram_mb = discovery.ram_mb or node.ram_mb
        node.disk_gb = discovery.disk_gb or node.disk_gb
        node.ip_address = discovery.ip_address or node.ip_address
        node.last_seen = now

        meta = dict(node.metadata_ or {})
        meta.update(discovery.metadata)
        meta["canonical_identity"] = discovery.canonical_identity
        node.metadata_ = meta
        await db.flush()

    # Process child nodes recursively (e.g. VMs or Containers under Host)
    for child_discovery in discovery.children:
        await process_discovery_result(db, child_discovery, parent_id=node.id)

    await db.commit()
    await db.refresh(node)
    return node
