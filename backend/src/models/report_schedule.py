from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base
from models.base import TimestampMixin, UUIDMixin


def utc_now() -> datetime:
    return datetime.now(UTC)


class ReportSchedule(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "report_schedules"

    name: Mapped[str] = mapped_column(String(128), nullable=False)
    frequency: Mapped[str] = mapped_column(String(32), default="weekly", nullable=False) # "weekly", "monthly", "daily"
    report_type: Mapped[str] = mapped_column(String(32), default="weekly", nullable=False) # "weekly", "monthly"
    export_format: Mapped[str] = mapped_column(String(32), default="pdf", nullable=False) # "pdf", "excel", "both"

    # Store email recipient addresses as JSON list inside dictionary: {"emails": ["exec@company.com"]}
    recipients: Mapped[dict[str, Any]] = mapped_column(
        JSONB().with_variant(JSON(), "sqlite"), default=dict, nullable=False, server_default="{}"
    )

    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    next_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
