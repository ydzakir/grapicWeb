import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy import (
    Enum as SQLEnum,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base
from models.base import GUID, TimestampMixin, UUIDMixin


class AlertSeverity(enum.StrEnum):
    WARNING = "warning"
    CRITICAL = "critical"


class AlertStatus(enum.StrEnum):
    FIRING = "firing"
    RESOLVED = "resolved"
    ACKNOWLEDGED = "acknowledged"


class AlertRule(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "alert_rules"

    node_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID, ForeignKey("nodes.id", ondelete="CASCADE"), nullable=True, index=True
    )
    group_name: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    metric_name: Mapped[str] = mapped_column(String(64), nullable=False) # cpu_usage, ram_usage, disk_usage, node_status
    warning_threshold: Mapped[float | None] = mapped_column(Float, nullable=True)
    critical_threshold: Mapped[float | None] = mapped_column(Float, nullable=True)
    duration_seconds: Mapped[int] = mapped_column(Integer, default=300, nullable=False) # 5m default
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Alert(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "alerts"

    node_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("nodes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    rule_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID, ForeignKey("alert_rules.id", ondelete="SET NULL"), nullable=True
    )
    severity: Mapped[AlertSeverity] = mapped_column(
        SQLEnum(AlertSeverity, name="alert_severity_enum"), nullable=False, index=True
    )
    status: Mapped[AlertStatus] = mapped_column(
        SQLEnum(AlertStatus, name="alert_status_enum"), default=AlertStatus.FIRING, nullable=False, index=True
    )
    message: Mapped[str] = mapped_column(Text, nullable=False)
    triggered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    acknowledged_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    last_notified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    escalated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    ticket_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    ticket_url: Mapped[str | None] = mapped_column(String(256), nullable=True)
    ticket_system: Mapped[str | None] = mapped_column(String(32), nullable=True)
    ticket_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    ticket_created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("idx_alerts_status_severity", "status", "severity"),
    )


class NotificationProvider(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "notification_providers"

    name: Mapped[str] = mapped_column(String(64), nullable=False)
    provider_type: Mapped[str] = mapped_column(String(32), nullable=False) # log, webhook, email
    config: Mapped[dict[str, Any]] = mapped_column(
        JSONB().with_variant(JSON(), "sqlite"), default=dict, nullable=False, server_default="{}"
    )
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
