from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, DateTime, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base
from models.base import TimestampMixin, UUIDMixin


def utc_now() -> datetime:
    return datetime.now(UTC)


class QuarterlyAuditReview(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "quarterly_audit_reviews"

    quarter: Mapped[str] = mapped_column(String(32), nullable=False, index=True) # e.g. "2026-Q3"
    title: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="IN_REVIEW", nullable=False, index=True) # IN_REVIEW, APPROVED, REJECTED, OVERDUE_ESCALATED
    reviewer_username: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    due_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Snapshot of users, roles, and node permissions at campaign creation
    user_snapshots: Mapped[dict[str, Any]] = mapped_column(
        JSONB().with_variant(JSON(), "sqlite"), default=dict, nullable=False, server_default="{}"
    )
    # Reviewer decisions per user_id: { user_id: { "decision": "approve"|"revoke"|"modify_role", "notes": "...", "reviewed_at": "..." } }
    review_decisions: Mapped[dict[str, Any]] = mapped_column(
        JSONB().with_variant(JSON(), "sqlite"), default=dict, nullable=False, server_default="{}"
    )

    signoff_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    signoff_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    digital_signature: Mapped[str | None] = mapped_column(String(128), nullable=True)
    comments: Mapped[str | None] = mapped_column(Text, nullable=True)
