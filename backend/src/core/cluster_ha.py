"""Cluster HA — leader election & failover synchronization.

Honest, minimal High Availability support for the monitoring backend.

Design:
- Leader election is coordinated through a PostgreSQL advisory lock, which is
  safe across multiple backend replicas sharing the same database (the HA
  compose stack routes all backends through PgBouncer).
- A single worker/backend instance becomes the "leader" and is responsible for
  running the collector polling cycle and the report cron engine.
- The API exposes the current cluster state so operators can verify which
  replica is leading and whether failover occurred.

This deliberately does NOT attempt active-active in-memory WebSocket fan-out
across replicas; each replica keeps its own connection manager and the reverse
proxy (nginx) load-balances clients.
"""
import logging
import os
import uuid
from datetime import UTC, datetime

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger("cluster_ha")

_HEARTBEAT_TABLE = "cluster_ha_heartbeats"
_HEARTBEAT_INTERVAL_SECONDS = 10
_HEARTBEAT_STALE_SECONDS = 30

# In-memory leader state for this process.
_leader_id: str | None = None
_is_leader = False


def utc_now() -> datetime:
    return datetime.now(UTC)


def generate_node_id() -> str:
    """Return a stable per-process node identifier from env or a new UUID."""
    return os.getenv("HA_NODE_ID") or f"backend-{uuid.uuid4().hex[:8]}"


async def _ensure_heartbeat_table(db: AsyncSession) -> None:
    await db.execute(
        text(
            f"""
            CREATE TABLE IF NOT EXISTS {_HEARTBEAT_TABLE} (
                node_id TEXT PRIMARY KEY,
                last_seen TIMESTAMPTZ NOT NULL
            )
            """
        )
    )


async def acquire_leader_lock(db: AsyncSession) -> bool:
    """
    Try to become the cluster leader using a PostgreSQL advisory lock.
    Returns True if this process is the leader.

    On non-PostgreSQL backends (e.g. SQLite for tests/dev) advisory locks are
    unavailable, so the process reports itself as leader (single-node mode).
    """
    global _leader_id, _is_leader
    if not _leader_id:
        _leader_id = generate_node_id()

    if db.bind is not None and getattr(db.bind, "dialect", None) is not None:
        if db.bind.dialect.name != "postgresql":
            _is_leader = True
            return True

    # Advisory lock key (arbitrary but stable across replicas)
    result = await db.execute(
        text("SELECT pg_try_advisory_lock(:key)"),
        {"key": 0x4D4F4E49},  # 'MONI'
    )
    locked = result.scalar()
    return bool(locked)


async def release_leader_lock(db: AsyncSession) -> None:
    """Release the advisory lock if this process holds it."""
    if db.bind is not None and getattr(db.bind, "dialect", None) is not None:
        if db.bind.dialect.name != "postgresql":
            return
    await db.execute(text("SELECT pg_advisory_unlock(:key)"), {"key": 0x4D4F4E49})


async def update_heartbeat(db: AsyncSession, node_id: str) -> None:
    """Update this node's heartbeat row in the shared table."""
    await _ensure_heartbeat_table(db)
    await db.execute(
        text(
            f"""
            INSERT INTO {_HEARTBEAT_TABLE} (node_id, last_seen)
            VALUES (:node_id, :ts)
            ON CONFLICT (node_id) DO UPDATE SET last_seen = :ts
            """
        ),
        {"node_id": node_id, "ts": utc_now()},
    )
    await db.commit()


async def remove_heartbeat(db: AsyncSession, node_id: str) -> None:
    await _ensure_heartbeat_table(db)
    await db.execute(
        text(f"DELETE FROM {_HEARTBEAT_TABLE} WHERE node_id = :node_id"),
        {"node_id": node_id},
    )
    await db.commit()


async def get_cluster_state(db: AsyncSession) -> dict:
    """
    Return the current cluster state: heartbeat rows + leader detection.
    A heartbeat row is considered active if last_seen is within the stale window.
    """
    await _ensure_heartbeat_table(db)
    result = await db.execute(
        text(
            f"SELECT node_id, last_seen FROM {_HEARTBEAT_TABLE} ORDER BY last_seen DESC"
        )
    )
    rows = result.all()
    now = utc_now()

    members = []
    for node_id, last_seen in rows:
        if isinstance(last_seen, str):
            try:
                last_seen = datetime.fromisoformat(last_seen)
            except Exception:
                last_seen = utc_now()
        last_seen_utc = last_seen if getattr(last_seen, "tzinfo", None) else last_seen.replace(tzinfo=UTC)
        is_active = (now - last_seen_utc).total_seconds() < _HEARTBEAT_STALE_SECONDS
        members.append(
            {
                "node_id": node_id,
                "last_seen": last_seen_utc.isoformat(),
                "active": is_active,
            }
        )

    return {
        "ha_mode_enabled": bool(os.getenv("HA_MODE_ENABLED")),
        "current_node_id": _leader_id,
        "am_i_leader": _is_leader,
        "members": members,
    }


async def cluster_leader_cycle(db: AsyncSession) -> bool:
    """
    Runs the leader election + heartbeat cycle. Returns True if this process
    should act as the leader for this cycle.
    """
    global _is_leader

    is_leader = await acquire_leader_lock(db)
    _is_leader = is_leader

    node_id = _leader_id or generate_node_id()
    if is_leader:
        await update_heartbeat(db, node_id)
    else:
        # Non-leader still records presence so cluster state is visible
        await update_heartbeat(db, node_id)

    await db.rollback()
    return is_leader
