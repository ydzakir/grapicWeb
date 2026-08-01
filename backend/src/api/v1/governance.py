import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_user, require_role
from core.database import get_db
from models.governance import QuarterlyAuditReview
from models.user import User, UserRole
from schemas.governance import (
    AuditReviewCreateRequest,
    AuditReviewResponse,
    ComplianceReportResponse,
    ReviewDecisionSubmit,
    SignOffRequest,
)
from services.governance_service import (
    create_quarterly_audit_campaign,
    executive_signoff,
    generate_compliance_report,
    process_reviewer_escalations,
    submit_review_decision,
)

require_admin_role = require_role([UserRole.ADMIN])

router = APIRouter(prefix="/governance", tags=["Governance & Quarterly Audit Review"])


@router.get("/reviews", response_model=List[AuditReviewResponse])
async def list_audit_reviews(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve all quarterly audit review campaigns."""
    stmt = select(QuarterlyAuditReview).order_by(desc(QuarterlyAuditReview.created_at))
    res = await db.execute(stmt)
    return res.scalars().all()


@router.post("/reviews", response_model=AuditReviewResponse, status_code=status.HTTP_201_CREATED)
async def create_audit_review_campaign_endpoint(
    body: AuditReviewCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin_role),
):
    """Create a new quarterly audit review campaign and snapshot user RBAC access (Admin only)."""
    campaign = await create_quarterly_audit_campaign(
        db=db,
        quarter=body.quarter,
        title=body.title,
        reviewer_username=body.reviewer_username,
        duration_days=body.duration_days,
        created_by=current_user.username,
    )
    return campaign


@router.get("/reviews/{review_id}", response_model=AuditReviewResponse)
async def get_audit_review_detail(
    review_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve details and user snapshots for a specific audit review campaign."""
    campaign = await db.get(QuarterlyAuditReview, review_id)
    if not campaign:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audit campaign not found")
    return campaign


@router.post("/reviews/{review_id}/decisions", response_model=AuditReviewResponse)
async def submit_review_decision_endpoint(
    review_id: uuid.UUID,
    body: ReviewDecisionSubmit,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Submit or update access review decision for a user in the campaign."""
    try:
        updated_campaign = await submit_review_decision(
            db=db,
            review_id=review_id,
            user_id=body.user_id,
            decision=body.decision,
            new_role=body.new_role,
            notes=body.notes,
            reviewer_username=current_user.username,
        )
        return updated_campaign
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/reviews/{review_id}/sign-off", response_model=AuditReviewResponse)
async def executive_signoff_endpoint(
    review_id: uuid.UUID,
    body: SignOffRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin_role),
):
    """Formal Executive Sign-off for a quarterly audit review (Admin/Compliance Lead only)."""
    try:
        signed_campaign = await executive_signoff(
            db=db,
            review_id=review_id,
            signoff_by=current_user.username,
            comments=body.comments,
        )
        return signed_campaign
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/reviews/{review_id}/compliance-report", response_model=ComplianceReportResponse)
async def get_compliance_report_endpoint(
    review_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate executive compliance report for a quarterly audit review campaign."""
    try:
        report = await generate_compliance_report(db=db, review_id=review_id)
        return report
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/reviews/process-escalations")
async def trigger_reviewer_escalations_endpoint(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin_role),
):
    """Trigger automated reviewer escalation engine for overdue audit reviews."""
    escalated = await process_reviewer_escalations(db=db)
    return {
        "status": "success",
        "escalated_count": len(escalated),
        "escalated_campaigns": [str(c.id) for c in escalated],
    }
