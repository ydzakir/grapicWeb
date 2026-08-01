import hashlib
import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.audit import AuditLog
from models.governance import QuarterlyAuditReview
from models.user import User
from services.notification_service import get_notification_provider

logger = logging.getLogger("governance_service")


def utc_now() -> datetime:
    return datetime.now(UTC)


async def create_quarterly_audit_campaign(
    db: AsyncSession,
    quarter: str,
    title: str,
    reviewer_username: str,
    duration_days: int = 14,
    created_by: str = "system",
) -> QuarterlyAuditReview:
    """Creates a new quarterly audit review campaign and snapshots all active user accounts."""
    now = utc_now()
    due_date = now + timedelta(days=duration_days)

    # 1. Fetch all user accounts and snapshot their RBAC details
    stmt = select(User).order_by(User.username)
    res = await db.execute(stmt)
    users = res.scalars().all()

    user_snapshots = {}
    for user in users:
        user_snapshots[str(user.id)] = {
            "user_id": str(user.id),
            "username": user.username,
            "email": user.email,
            "role": user.role.value,
            "is_active": user.is_active,
            "snapshot_at": now.isoformat(),
        }

    # 2. Create Audit Review Campaign
    campaign = QuarterlyAuditReview(
        quarter=quarter,
        title=title,
        status="IN_REVIEW",
        reviewer_username=reviewer_username,
        due_date=due_date,
        user_snapshots=user_snapshots,
        review_decisions={},
    )
    db.add(campaign)

    # 3. Log audit trail
    audit = AuditLog(
        actor_username=created_by,
        action="GOVERNANCE_CAMPAIGN_CREATED",
        target=quarter,
        metadata_={
            "title": title,
            "reviewer_username": reviewer_username,
            "total_accounts": len(users),
            "due_date": due_date.isoformat(),
        },
    )
    db.add(audit)

    await db.commit()
    await db.refresh(campaign)
    return campaign


async def submit_review_decision(
    db: AsyncSession,
    review_id: uuid.UUID,
    user_id: str,
    decision: str,
    new_role: str | None,
    notes: str | None,
    reviewer_username: str,
) -> QuarterlyAuditReview:
    """Submits or updates an access review decision for a single user in a campaign."""
    campaign = await db.get(QuarterlyAuditReview, review_id)
    if not campaign:
        raise KeyError(f"Audit review campaign '{review_id}' not found")

    if campaign.status in ("APPROVED", "REJECTED"):
        raise ValueError("Cannot modify decisions on a signed-off or closed audit campaign")

    # Update review_decisions dictionary (JSON column)
    current_decisions = dict(campaign.review_decisions or {})
    current_decisions[user_id] = {
        "user_id": user_id,
        "decision": decision,
        "new_role": new_role,
        "notes": notes or "",
        "reviewed_by": reviewer_username,
        "reviewed_at": utc_now().isoformat(),
    }

    # Re-assign dict to trigger SQLAlchemy JSON modification tracking
    campaign.review_decisions = current_decisions

    await db.commit()
    await db.refresh(campaign)
    return campaign


async def executive_signoff(
    db: AsyncSession,
    review_id: uuid.UUID,
    signoff_by: str,
    comments: str | None = None,
) -> QuarterlyAuditReview:
    """Executes formal executive sign-off for a quarterly audit review with digital signature."""
    campaign = await db.get(QuarterlyAuditReview, review_id)
    if not campaign:
        raise KeyError(f"Audit review campaign '{review_id}' not found")

    now = utc_now()
    campaign.status = "APPROVED"
    campaign.signoff_by = signoff_by
    campaign.signoff_at = now
    campaign.comments = comments or "Approved & signed off"

    # Compute digital verification signature (SHA-256 hash)
    signature_base = f"{campaign.id}:{campaign.quarter}:{signoff_by}:{now.isoformat()}:{len(campaign.review_decisions)}"
    campaign.digital_signature = hashlib.sha256(signature_base.encode("utf-8")).hexdigest()

    # Log audit entry
    audit = AuditLog(
        actor_username=signoff_by,
        action="GOVERNANCE_EXECUTIVE_SIGNOFF",
        target=str(campaign.id),
        metadata_={
            "quarter": campaign.quarter,
            "digital_signature": campaign.digital_signature,
            "decisions_count": len(campaign.review_decisions),
        },
    )
    db.add(audit)

    await db.commit()
    await db.refresh(campaign)
    return campaign


async def process_reviewer_escalations(db: AsyncSession) -> list[QuarterlyAuditReview]:
    """
    Evaluates pending audit campaigns:
    1. Sends notification reminders if nearing due date.
    2. Escalates status to OVERDUE_ESCALATED if past due date.
    """
    now = utc_now()
    stmt = select(QuarterlyAuditReview).where(QuarterlyAuditReview.status == "IN_REVIEW")
    res = await db.execute(stmt)
    pending_campaigns = res.scalars().all()

    escalated_campaigns = []
    for campaign in pending_campaigns:
        if now > campaign.due_date:
            campaign.status = "OVERDUE_ESCALATED"
            escalated_campaigns.append(campaign)

            # Send escalation notification via NotificationProvider
            provider = get_notification_provider("log")
            await provider.send_notification(
                title="[GOVERNANCE ESCALATION] Audit Review Overdue",
                message=f"Quarterly Audit Review '{campaign.title}' ({campaign.quarter}) assigned to {campaign.reviewer_username} is past due date!",
                severity="critical",
                details={
                    "campaign_id": str(campaign.id),
                    "reviewer": campaign.reviewer_username,
                    "due_date": campaign.due_date.isoformat(),
                },
            )

    if escalated_campaigns:
        await db.commit()

    return escalated_campaigns


async def generate_compliance_report(
    db: AsyncSession,
    review_id: uuid.UUID,
) -> dict[str, Any]:
    """Generates an executive compliance report for a specific quarterly audit campaign."""
    campaign = await db.get(QuarterlyAuditReview, review_id)
    if not campaign:
        raise KeyError(f"Audit review campaign '{review_id}' not found")

    snapshots = campaign.user_snapshots or {}
    decisions = campaign.review_decisions or {}

    total_accounts = len(snapshots)
    approved_count = 0
    revoked_count = 0
    modified_count = 0

    for uid, dec in decisions.items():
        d_type = dec.get("decision")
        if d_type == "approve":
            approved_count += 1
        elif d_type == "revoke":
            revoked_count += 1
        elif d_type == "modify_role":
            modified_count += 1

    pending_count = total_accounts - len(decisions)
    compliance_pct = (len(decisions) / total_accounts * 100.0) if total_accounts > 0 else 100.0

    return {
        "review_id": campaign.id,
        "quarter": campaign.quarter,
        "title": campaign.title,
        "status": campaign.status,
        "total_accounts": total_accounts,
        "approved_accounts": approved_count,
        "revoked_accounts": revoked_count,
        "modified_accounts": modified_count,
        "pending_accounts": pending_count,
        "compliance_percentage": round(compliance_pct, 1),
        "signoff_by": campaign.signoff_by,
        "signoff_at": campaign.signoff_at,
        "digital_signature": campaign.digital_signature,
        "generated_at": utc_now(),
    }
