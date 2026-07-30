import enum
import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import (
    JSON,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy import (
    Enum as SQLEnum,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base
from models.base import GUID, TimestampMixin, UUIDMixin


class NodeType(enum.StrEnum):
    DATA_CENTER = "data_center"
    PHYSICAL_SERVER = "physical_server"
    HYPERV_HOST = "hyperv_host"
    HYPERVISOR_HOST = "hyperv_host"
    HYPERV_VM = "hyperv_vm"
    VM = "hyperv_vm"
    DOCKER_HOST = "docker_host"
    DOCKER_CONTAINER = "docker_container"
    CONTAINER = "docker_container"


class NodeStatus(enum.StrEnum):
    UP = "up"
    DOWN = "down"
    WARNING = "warning"
    UNKNOWN = "unknown"


class ReviewStatus(enum.StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class LifecycleStatus(enum.StrEnum):
    ACTIVE = "active"
    ARCHIVED = "archived"


class ConnectionType(enum.StrEnum):
    NETWORK = "network"
    HOSTS = "hosts"
    DEPENDS_ON = "depends_on"


class Node(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "nodes"

    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    type: Mapped[NodeType] = mapped_column(
        SQLEnum(NodeType, name="node_type_enum"), nullable=False, index=True
    )
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID,
        ForeignKey("nodes.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    os: Mapped[str | None] = mapped_column(String(128), nullable=True)
    cpu_cores: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ram_mb: Mapped[int | None] = mapped_column(Integer, nullable=True)
    disk_gb: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True, index=True)
    status: Mapped[NodeStatus] = mapped_column(
        SQLEnum(NodeStatus, name="node_status_enum"),
        default=NodeStatus.UNKNOWN,
        nullable=False,
        index=True,
    )
    review_status: Mapped[ReviewStatus] = mapped_column(
        SQLEnum(ReviewStatus, name="review_status_enum"),
        default=ReviewStatus.PENDING,
        nullable=False,
        index=True,
    )
    lifecycle_status: Mapped[LifecycleStatus] = mapped_column(
        SQLEnum(LifecycleStatus, name="lifecycle_status_enum"),
        default=LifecycleStatus.ACTIVE,
        nullable=False,
        index=True,
    )
    last_seen: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB().with_variant(JSON(), "sqlite"),
        default=dict,
        nullable=False,
        server_default="{}",
    )

    # Relationships
    parent: Mapped[Optional["Node"]] = relationship(
        "Node", remote_side="Node.id", backref="children"
    )

    __table_args__ = (
        Index("idx_nodes_type_status", "type", "status"),
        Index("idx_nodes_review_lifecycle", "review_status", "lifecycle_status"),
    )


class NodeConnection(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "node_connections"

    source_node_id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        ForeignKey("nodes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    target_node_id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        ForeignKey("nodes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    connection_type: Mapped[ConnectionType] = mapped_column(
        SQLEnum(ConnectionType, name="connection_type_enum"),
        default=ConnectionType.DEPENDS_ON,
        nullable=False,
    )
    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB().with_variant(JSON(), "sqlite"),
        default=dict,
        nullable=False,
        server_default="{}",
    )

    # Prevent duplicate edges between same nodes of same type
    __table_args__ = (
        UniqueConstraint(
            "source_node_id",
            "target_node_id",
            "connection_type",
            name="uq_node_connection_edge",
        ),
    )
