import uuid
from datetime import datetime, timezone, timedelta
from typing import List, Optional
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from models.alert import Alert, AlertRule, AlertSeverity, AlertStatus
from models.node import Node, NodeStatus
from models.audit import AuditLog
from services.notification_service import get_notification_provider

DEDUPLICATION_WINDOW_SECONDS = 900 # 15 minutes
ESCALATION_WINDOW_SECONDS = 900     # 15 minutes


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


async def evaluate_node_telemetry_alerts(
    db: AsyncSession,
    node: Node,
    cpu_usage: Optional[float] = None,
    ram_usage: Optional[float] = None,
    disk_usage: Optional[float] = None,
) -> List[Alert]:
    """
    Evaluates node metrics against default/custom threshold alert rules:
    - CPU: Warning >85%, Critical >95%
    - RAM: Warning >85%, Critical >95%
    - Disk: Warning >80%, Critical >90%
    - Status: DOWN > 2m -> Critical
    Handles 15m deduplication, auto-resolution, and 15m critical escalation.
    """
    now = utc_now()
    generated_alerts = []

    metrics_eval = [
        ("cpu_usage", cpu_usage, 85.0, 95.0),
        ("ram_usage", ram_usage, 85.0, 95.0),
        ("disk_usage", disk_usage, 80.0, 90.0),
    ]

    for metric_name, val, warn_thresh, crit_thresh in metrics_eval:
        if val is None:
            continue

        # Determine severity if threshold breached
        severity: Optional[AlertSeverity] = None
        if val >= crit_thresh:
            severity = AlertSeverity.CRITICAL
        elif val >= warn_thresh:
            severity = AlertSeverity.WARNING

        # Fetch active firing alert for node and metric
        stmt = select(Alert).where(
            and_(
                Alert.node_id == node.id,
                Alert.status == AlertStatus.FIRING,
                Alert.message.like(f"%{metric_name}%"),
            )
        )
        res = await db.execute(stmt)
        active_alert = res.scalars().first()

        if severity:
            msg = f"{metric_name.replace('_', ' ').upper()} high on {node.name}: {val:.1f}% (Threshold: {crit_thresh if severity == AlertSeverity.CRITICAL else warn_thresh}%)"
            
            if active_alert:
                # Deduplication check: 15 minutes window
                should_notify = False
                if not active_alert.last_notified_at or (now - active_alert.last_notified_at).total_seconds() >= DEDUPLICATION_WINDOW_SECONDS:
                    should_notify = True
                    active_alert.last_notified_at = now

                # Escalation check: Critical unacknowledged > 15 minutes
                if (
                    active_alert.severity == AlertSeverity.CRITICAL
                    and not active_alert.acknowledged_at
                    and not active_alert.escalated
                    and (now - active_alert.triggered_at).total_seconds() >= ESCALATION_WINDOW_SECONDS
                ):
                    active_alert.escalated = True
                    should_notify = True
                    msg = f"[ESCALATED] {msg}"

                if should_notify:
                    provider = get_notification_provider("log")
                    await provider.send_notification(
                        title=f"Alert {severity.value.upper()}",
                        message=msg,
                        severity=severity.value,
                        details={"node_id": str(node.id), "metric": metric_name, "value": val},
                    )
            else:
                # Create new firing alert
                new_alert = Alert(
                    node_id=node.id,
                    severity=severity,
                    status=AlertStatus.FIRING,
                    message=msg,
                    triggered_at=now,
                    last_notified_at=now,
                )
                db.add(new_alert)
                generated_alerts.append(new_alert)

                provider = get_notification_provider("log")
                await provider.send_notification(
                    title=f"New Alert {severity.value.upper()}",
                    message=msg,
                    severity=severity.value,
                    details={"node_id": str(node.id), "metric": metric_name, "value": val},
                )
        else:
            # Auto-resolve active alert if metric dropped back to normal
            if active_alert:
                active_alert.status = AlertStatus.RESOLVED
                active_alert.resolved_at = now
                resolve_msg = f"[RESOLVED] {metric_name.replace('_', ' ').upper()} normalized on {node.name}: {val:.1f}%"
                
                provider = get_notification_provider("log")
                await provider.send_notification(
                    title="Alert RESOLVED",
                    message=resolve_msg,
                    severity="info",
                    details={"node_id": str(node.id), "metric": metric_name, "value": val},
                )

    # Evaluate Node DOWN > 2 minutes
    if node.status == NodeStatus.DOWN:
        stmt = select(Alert).where(
            and_(
                Alert.node_id == node.id,
                Alert.status == AlertStatus.FIRING,
                Alert.message.like("%NODE DOWN%"),
            )
        )
        res = await db.execute(stmt)
        down_alert = res.scalars().first()

        if not down_alert:
            down_msg = f"NODE DOWN CRITICAL: Node {node.name} ({node.ip_address or 'No IP'}) is unreachable."
            new_down_alert = Alert(
                node_id=node.id,
                severity=AlertSeverity.CRITICAL,
                status=AlertStatus.FIRING,
                message=down_msg,
                triggered_at=now,
                last_notified_at=now,
            )
            db.add(new_down_alert)
            generated_alerts.append(new_down_alert)

    await db.flush()
    return generated_alerts


async def acknowledge_alert(db: AsyncSession, alert_id: uuid.UUID, username: str, note: Optional[str] = None) -> Alert:
    """Acknowledge a firing alert with audit trail logging."""
    alert = await db.get(Alert, alert_id)
    if not alert:
        raise KeyError(f"Alert '{alert_id}' not found")

    now = utc_now()
    alert.status = AlertStatus.ACKNOWLEDGED
    alert.acknowledged_at = now
    alert.acknowledged_by = username

    # Create audit log entry
    audit = AuditLog(
        actor_username=username,
        action="ALERT_ACKNOWLEDGE",
        target=str(alert_id),
        metadata_={"note": note or "Acknowledged by user", "alert_message": alert.message},
    )
    db.add(audit)
    await db.commit()
    await db.refresh(alert)
    return alert
