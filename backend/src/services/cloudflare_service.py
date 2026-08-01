from datetime import UTC, datetime

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from collectors.cloudflare_collector import (
    CloudflareCollectorAdapter,
    CloudflareStatusSummary,
)
from models.alert import Alert, AlertSeverity, AlertStatus
from models.node import Node, NodeStatus, NodeType, ReviewStatus

_cloudflare_cache: CloudflareStatusSummary | None = None
_last_sync_time: datetime | None = None


async def get_cloudflare_edge_status() -> CloudflareStatusSummary:
    global _cloudflare_cache, _last_sync_time
    # Cache for 60 seconds
    now = datetime.now(UTC)
    if _cloudflare_cache is not None and _last_sync_time is not None:
        if (now - _last_sync_time).total_seconds() < 60:
            return _cloudflare_cache

    adapter = CloudflareCollectorAdapter()
    summary = await adapter.fetch_status_summary()
    _cloudflare_cache = summary
    _last_sync_time = now
    return summary


async def sync_cloudflare_and_evaluate_alerts(db: AsyncSession) -> CloudflareStatusSummary:
    """
    Syncs Cloudflare Edge status and triggers active alerts if global edge or components fail.
    """
    summary = await get_cloudflare_edge_status()
    now = datetime.now(UTC)

    # Find or create Cloudflare Edge synthetic node in inventory
    stmt = select(Node).where(Node.name == "edge-cloudflare-global")
    res = await db.execute(stmt)
    cf_node = res.scalar_one_or_none()

    if not cf_node:
        cf_node = Node(
            name="edge-cloudflare-global",
            type=NodeType.SERVICE,
            ip_address="1.1.1.1",
            os="Cloudflare Edge OS",
            status=NodeStatus.UP,
            review_status=ReviewStatus.APPROVED,
            metadata_={
                "provider": "Cloudflare",
                "indicator": summary.global_indicator,
                "description": summary.global_description,
            },
        )

        db.add(cf_node)
        await db.flush()


    # Alert Evaluation for Cloudflare Outage / Degradation
    indicator = summary.global_indicator.lower()
    has_incident = len(summary.incidents) > 0 or indicator in ["minor", "major", "critical"]

    # Check existing firing alert for Cloudflare
    alert_stmt = select(Alert).where(
        and_(
            Alert.node_id == cf_node.id,
            Alert.status == AlertStatus.FIRING,
            Alert.message.like("%Cloudflare Edge%"),
        )
    )
    existing_alert = (await db.execute(alert_stmt)).scalar_one_or_none()

    if has_incident:
        severity = AlertSeverity.CRITICAL if indicator in ["major", "critical"] else AlertSeverity.WARNING
        msg = f"Cloudflare Edge Alert: {summary.global_description} (Indicator: {summary.global_indicator})"

        if not existing_alert:
            new_alert = Alert(
                node_id=cf_node.id,
                severity=severity,
                status=AlertStatus.FIRING,
                message=msg,
                triggered_at=now,
                created_at=now,
                updated_at=now,
            )
            db.add(new_alert)
        else:
            existing_alert.severity = severity
            existing_alert.message = msg
            existing_alert.updated_at = now
    else:
        # Resolve existing alert if Cloudflare returns to operational status
        if existing_alert:
            existing_alert.status = AlertStatus.RESOLVED
            existing_alert.resolved_at = now
            existing_alert.updated_at = now

    await db.commit()
    return summary

