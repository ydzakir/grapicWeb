from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.node import LifecycleStatus, Node, ReviewStatus
from schemas.metrics import StatusDeltaMessage
from services.websocket_manager import status_ws_manager


def utc_now() -> datetime:
    return datetime.now(UTC)


_last_broadcast_status: dict[str, str] = {}


def reset_broadcast_tracker() -> None:
    """Clear the in-process status-change tracker (used by tests)."""
    _last_broadcast_status.clear()


async def broadcast_status_deltas(db: AsyncSession) -> int:
    """
    Broadcast real status deltas for approved, active nodes to all connected
    WebSocket clients. A delta is only sent when the node status actually
    changed since the last broadcast, so the frontend receives lightweight
    live updates without refetching the full graph.

    Returns the number of status-change deltas broadcast.
    """
    stmt = select(Node).where(
        Node.review_status == ReviewStatus.APPROVED,
        Node.lifecycle_status == LifecycleStatus.ACTIVE,
    )
    result = await db.execute(stmt)
    nodes = list(result.scalars().all())

    changed_count = 0
    for node in nodes:
        node_key = str(node.id)
        new_status = node.status.value
        if _last_broadcast_status.get(node_key) == new_status:
            continue

        delta = StatusDeltaMessage(
            node_id=node_key,
            name=node.name,
            type=node.type.value,
            status=new_status,
            last_seen=(
                node.last_seen.isoformat() if node.last_seen else None
            ),
            timestamp=utc_now().isoformat(),
        )
        await status_ws_manager.broadcast_status_delta(delta)
        _last_broadcast_status[node_key] = new_status
        changed_count += 1

    return changed_count


async def broadcast_node_status_change(
    node_id: str,
    name: str,
    node_type: str,
    status: str,
    last_seen: str | None = None,
) -> None:
    """
    Broadcast a single immediate status delta (called by the collector worker
    right after a status transition so clients get updates without waiting for
    the periodic broadcaster).
    """
    delta = StatusDeltaMessage(
        node_id=node_id,
        name=name,
        type=node_type,
        status=status,
        last_seen=last_seen,
        timestamp=utc_now().isoformat(),
    )
    await status_ws_manager.broadcast_status_delta(delta)
    _last_broadcast_status[node_id] = status
