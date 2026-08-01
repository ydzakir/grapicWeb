import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_user, require_granular_permission, require_role
from core.database import get_db
from models.alert import Alert, AlertRule, AlertStatus
from models.user import User, UserRole
from schemas.alert import (
    AlertAcknowledgeRequest,
    AlertResponse,
    AlertRuleCreate,
    AlertRuleResponse,
    CreateTicketRequest,
    TicketingWebhookCallback,
)
from services.alert_service import acknowledge_alert
from services.ticketing_service import (
    create_ticket_for_alert,
    handle_ticket_webhook_callback,
    sync_alert_ticket_status,
)

require_admin_role = require_role([UserRole.ADMIN])
require_alert_ack = require_granular_permission("alerts:ack")

router = APIRouter(prefix="/alerts", tags=["Alerts"])


@router.get("/active", response_model=list[AlertResponse])
async def get_active_alerts(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve all current firing alerts."""
    stmt = select(Alert).where(Alert.status == AlertStatus.FIRING).order_by(desc(Alert.triggered_at))
    res = await db.execute(stmt)
    return res.scalars().all()


@router.get("/history", response_model=list[AlertResponse])
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
    current_user: User = Depends(require_alert_ack),
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


@router.post("/{alert_id}/ticket", response_model=AlertResponse)
async def create_alert_ticket_endpoint(
    alert_id: uuid.UUID,
    body: CreateTicketRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Manually create an ITSM ticket (Jira / ServiceNow / ITSM Webhook) for an alert."""
    try:
        updated_alert = await create_ticket_for_alert(
            db=db,
            alert_id=alert_id,
            system_type=body.system_type,
            custom_params=body.model_dump(),
            username=current_user.username,
        )
        return updated_alert
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/{alert_id}/sync-ticket", response_model=AlertResponse)
async def sync_alert_ticket_endpoint(
    alert_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Synchronize ticket status with external ITSM system."""
    try:
        updated_alert = await sync_alert_ticket_status(db=db, alert_id=alert_id)
        return updated_alert
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/tickets/webhook-callback")
async def ticket_webhook_callback_endpoint(
    body: TicketingWebhookCallback,
    db: AsyncSession = Depends(get_db),
):
    """Receiver endpoint for Jira / ServiceNow status update webhooks."""
    updated_alert = await handle_ticket_webhook_callback(
        db=db,
        alert_id=body.alert_id,
        ticket_id=body.ticket_id,
        ticket_status=body.ticket_status,
        notes=body.notes,
    )
    if not updated_alert:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Matching alert/ticket not found")
    return {"status": "success", "alert_id": str(updated_alert.id), "ticket_status": updated_alert.ticket_status}


@router.get("/rules", response_model=list[AlertRuleResponse])
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

