import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class AuditReviewCreateRequest(BaseModel):
    quarter: str = Field(..., min_length=4, max_length=32) # e.g. "2026-Q3"
    title: str = Field(..., min_length=4, max_length=128)
    reviewer_username: str = Field(..., min_length=1, max_length=64)
    duration_days: int = Field(14, ge=1, le=90)


class ReviewDecisionSubmit(BaseModel):
    user_id: str = Field(..., min_length=1)
    decision: str = Field(..., pattern="^(approve|revoke|modify_role)$")
    new_role: Optional[str] = None
    notes: Optional[str] = None


class SignOffRequest(BaseModel):
    comments: Optional[str] = "Approved and signed off by Compliance Lead"


class AuditReviewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    quarter: str
    title: str
    status: str
    reviewer_username: str
    due_date: datetime
    user_snapshots: Dict[str, Any]
    review_decisions: Dict[str, Any]
    signoff_by: Optional[str] = None
    signoff_at: Optional[datetime] = None
    digital_signature: Optional[str] = None
    comments: Optional[str] = None
    created_at: datetime


class ComplianceReportResponse(BaseModel):
    review_id: uuid.UUID
    quarter: str
    title: str
    status: str
    total_accounts: int
    approved_accounts: int
    revoked_accounts: int
    modified_accounts: int
    pending_accounts: int
    compliance_percentage: float
    signoff_by: Optional[str] = None
    signoff_at: Optional[datetime] = None
    digital_signature: Optional[str] = None
    generated_at: datetime
