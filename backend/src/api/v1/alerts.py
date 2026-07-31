import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_user, require_role
from core.database import get_db
from models.alert import Alert, AlertRule, AlertStatus
from models.user import User, UserRole
from schemas.alert import AlertAcknowledgeRequest, AlertResponse, AlertRuleCreate, AlertRuleResponse
from services.alert_service import acknowledge_alert

require_admin_role = require_role([UserRole.ADMIN])

router = APIRouter(prefix="/alerts", tags=["Alerts"])


@router.get("/active", response_model=List[AlertResponse])
async def get_active_alerts(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve all current firing alerts."""
    stmt = select(Alert).where(Alert.status == AlertStatus.FIRING).order_by(desc(Alert.triggered_at))
    res = await db.execute(stmt)
    return res.scalars().all()


@router.get("/history", response_model=List[AlertResponse])
async def get_alert_history(
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve historical alert log."""
    stmt = select(Alert).order_by(desc(Alert.triggered_at)).limit(limit)
    res = await db.execute(stmt)
    return res.scalars().all()


@router.post("/{alert_id}/acknowledge", response_model=AlertResponse)
async def acknowledge_alert_endpoint(
    alert_id: uuid.UUID,
    body: AlertAcknowledgeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Acknowledge an active firing alert with audit trail."""
    try:
        updated_alert = await acknowledge_alert(
            db=db,
            alert_id=alert_id,
            username=current_user.username,
            note=body.note,
        )
        return updated_alert
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/rules", response_model=List[AlertRuleResponse])
async def get_alert_rules(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List configured alert rules."""
    stmt = select(AlertRule).order_by(desc(AlertRule.created_at))
    res = await db.execute(stmt)
    return res.scalars().all()


@router.post("/rules", response_model=AlertRuleResponse, status_code=status.HTTP_201_CREATED)
async def create_alert_rule(
    rule_in: AlertRuleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin_role),
):
    """Create a custom alert threshold rule (Admin only)."""
    rule = AlertRule(**rule_in.model_dump())
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    return rule
