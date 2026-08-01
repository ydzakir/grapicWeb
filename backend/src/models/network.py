import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
)
from sqlalchemy import (
    Enum as SQLEnum,
)
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base
from models.base import GUID, TimestampMixin, UUIDMixin


class EdgeConfidenceLevel(enum.StrEnum):
    HIGH = "high"       # Direct hypervisor / container socket API
    MEDIUM = "medium"   # SNMP / ARP table / ICMP discovery
    MANUAL = "manual"   # Manual operator definition


class Subnet(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "subnets"

    cidr: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    vlan_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    provenance: Mapped[str] = mapped_column(String(64), default="snmp_discovery", nullable=False)


class NetworkEdge(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "network_edges"

    source_node_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("nodes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    target_node_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("nodes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    connection_type: Mapped[str] = mapped_column(String(64), default="network_link", nullable=False)
    provenance: Mapped[str] = mapped_column(String(64), default="arp_discovery", nullable=False)
    confidence_level: Mapped[EdgeConfidenceLevel] = mapped_column(
        SQLEnum(EdgeConfidenceLevel, name="edge_confidence_level_enum"),
        default=EdgeConfidenceLevel.MEDIUM,
        nullable=False,
    )
    has_active_traffic: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    last_verified_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        Index("idx_network_edges_source_target", "source_node_id", "target_node_id", unique=True),
    )
