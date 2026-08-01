import pytest
from datetime import datetime, timedelta, timezone
from httpx import AsyncClient

from core.security import create_access_token
from models.governance import QuarterlyAuditReview
from models.user import User, UserRole
from services.governance_service import (
    create_quarterly_audit_campaign,
    executive_signoff,
    generate_compliance_report,
    process_reviewer_escalations,
    submit_review_decision,
)


@pytest.mark.asyncio
async def test_governance_service_workflow(db_session):
    """Test quarterly audit campaign creation, decision recording, sign-off, and compliance report."""
    # 1. Setup dummy user
    test_user = User(
        username="op_governance_target",
        email="target@infra.com",
        hashed_password="hash",
        role=UserRole.OPERATOR,
        is_active=True,
    )
    db_session.add(test_user)
    await db_session.commit()

    # 2. Create campaign
    campaign = await create_quarterly_audit_campaign(
        db=db_session,
        quarter="2026-Q3",
        title="2026 Q3 RBAC Access Review",
        reviewer_username="admin_lead",
        duration_days=14,
        created_by="admin_lead",
    )
    assert campaign.id is not None
    assert campaign.quarter == "2026-Q3"
    assert campaign.status == "IN_REVIEW"
    assert len(campaign.user_snapshots) >= 1

    # 3. Submit decision
    target_id = str(test_user.id)
    updated = await submit_review_decision(
        db=db_session,
        review_id=campaign.id,
        user_id=target_id,
        decision="approve",
        new_role=None,
        notes="Access re-verified and valid",
        reviewer_username="admin_lead",
    )
    assert target_id in updated.review_decisions
    assert updated.review_decisions[target_id]["decision"] == "approve"

    # 4. Executive sign-off
    signed = await executive_signoff(
        db=db_session,
        review_id=campaign.id,
        signoff_by="admin_lead",
        comments="Signoff complete",
    )
    assert signed.status == "APPROVED"
    assert signed.signoff_by == "admin_lead"
    assert signed.digital_signature is not None
    assert len(signed.digital_signature) == 64 # SHA-256 hex string

    # 5. Generate compliance report
    report = await generate_compliance_report(db=db_session, review_id=campaign.id)
    assert report["quarter"] == "2026-Q3"
    assert report["total_accounts"] >= 1
    assert report["compliance_percentage"] > 0.0


@pytest.mark.asyncio
async def test_reviewer_escalation_engine(db_session):
    """Test overdue audit review escalation engine."""
    past_due = datetime.now(timezone.utc) - timedelta(days=1)
    overdue_campaign = QuarterlyAuditReview(
        quarter="2026-Q1",
        title="Overdue Q1 Audit Review",
        status="IN_REVIEW",
        reviewer_username="slack_reviewer",
        due_date=past_due,
        user_snapshots={},
        review_decisions={},
    )
    db_session.add(overdue_campaign)
    await db_session.commit()

    escalated_list = await process_reviewer_escalations(db=db_session)
    assert len(escalated_list) >= 1
    assert overdue_campaign.status == "OVERDUE_ESCALATED"


@pytest.mark.asyncio
async def test_governance_api_endpoints(async_client: AsyncClient, db_session):
    """Test REST API endpoints for governance audit reviews."""
    admin = User(
        username="admin_gov_api",
        email="admin_gov@infra.com",
        hashed_password="hash",
        role=UserRole.ADMIN,
        is_active=True,
    )
    db_session.add(admin)
    await db_session.commit()
    token = create_access_token(subject=str(admin.id), role=admin.role.value)
    headers = {"Authorization": f"Bearer {token}"}

    # 1. POST /api/v1/governance/reviews
    create_resp = await async_client.post(
        "/api/v1/governance/reviews",
        json={
            "quarter": "2026-Q4",
            "title": "2026 Q4 Audit Review Campaign",
            "reviewer_username": "admin_gov_api",
            "duration_days": 30,
        },
        headers=headers,
    )
    assert create_resp.status_code == 201, create_resp.text
    camp_data = create_resp.json()
    review_id = camp_data["id"]
    assert camp_data["quarter"] == "2026-Q4"

    # 2. GET /api/v1/governance/reviews
    list_resp = await async_client.get("/api/v1/governance/reviews", headers=headers)
    assert list_resp.status_code == 200
    assert len(list_resp.json()) >= 1

    # 3. POST /api/v1/governance/reviews/{id}/sign-off
    signoff_resp = await async_client.post(
        f"/api/v1/governance/reviews/{review_id}/sign-off",
        json={"comments": "Final Q4 Signoff"},
        headers=headers,
    )
    assert signoff_resp.status_code == 200, signoff_resp.text
    assert signoff_resp.json()["status"] == "APPROVED"
    assert signoff_resp.json()["digital_signature"] is not None

    # 4. GET /api/v1/governance/reviews/{id}/compliance-report
    report_resp = await async_client.get(
        f"/api/v1/governance/reviews/{review_id}/compliance-report",
        headers=headers,
    )
    assert report_resp.status_code == 200
    assert report_resp.json()["digital_signature"] is not None
