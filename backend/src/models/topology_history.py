import uuid
from datetime import datetime, timezone
from typing import Any, Dict

from sqlalchemy import JSON, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base
from models.base import GUID, UUIDMixin


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class TopologySnapshot(Base, UUIDMixin):
    __tablename__ = "topology_snapshots"

    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False, index=True
    )
    node_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    edge_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    graph_json: Mapped[dict[str, Any]] = mapped_column(
        JSONB().with_variant(JSON(), "sqlite"), default=dict, nullable=False
    )


class TopologyChangeLog(Base, UUIDMixin):
    __tablename__ = "topology_change_logs"

    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False, index=True
    )
    action: Mapped[str] = mapped_column(String(64), nullable=False, index=True) # node_added, node_removed, edge_added, etc.
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)        # node, edge
    entity_id: Mapped[str] = mapped_column(String(128), nullable=False)
    details: Mapped[dict[str, Any]] = mapped_column(
        JSONB().with_variant(JSON(), "sqlite"), default=dict, nullable=False
    )
