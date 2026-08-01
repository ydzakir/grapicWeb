import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy import (
    Enum as SQLEnum,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base
from models.base import GUID, TimestampMixin, UUIDMixin


class TargetType(enum.StrEnum):
    SSH = "ssh"
    WINRM = "winrm"
    DOCKER_TLS = "docker_tls"
    FAKE = "fake"


class CollectorRunStatus(enum.StrEnum):
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"


class CollectorTarget(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "collector_targets"

    name: Mapped[str] = mapped_column(String(128), nullable=False)
    target_type: Mapped[TargetType] = mapped_column(
        SQLEnum(TargetType, name="target_type_enum"), nullable=False, index=True
    )
    host: Mapped[str] = mapped_column(String(255), nullable=False)
    port: Mapped[int] = mapped_column(Integer, nullable=False)
    credential_reference: Mapped[str] = mapped_column(
        String(255), nullable=False
    )  # Reference only, NEVER plaintext secret!
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB().with_variant(JSON(), "sqlite"),
        default=dict,
        nullable=False,
        server_default="{}",
    )

    @property
    def poll_interval_seconds(self) -> int:
        return int((self.metadata_ or {}).get("poll_interval_seconds", 60))

    runs: Mapped[list["CollectorRun"]] = relationship(
        "CollectorRun", back_populates="target", cascade="all, delete-orphan"
    )


class CollectorRun(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "collector_runs"

    target_id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        ForeignKey("collector_targets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[CollectorRunStatus] = mapped_column(
        SQLEnum(CollectorRunStatus, name="collector_run_status_enum"),
        nullable=False,
    )
    consecutive_failures: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )
    first_failure_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_attempt_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    target: Mapped["CollectorTarget"] = relationship(
        "CollectorTarget", back_populates="runs"
    )
