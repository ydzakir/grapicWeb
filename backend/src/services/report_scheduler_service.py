import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.alert import Alert
from models.audit import AuditLog
from models.node import Node
from models.report_schedule import ReportSchedule
from services.notification_service import get_notification_provider
from services.report_service import generate_excel_report, generate_pdf_report

logger = logging.getLogger("report_scheduler")


def utc_now() -> datetime:
    return datetime.now(UTC)


def calculate_next_run_at(frequency: str, from_time: datetime | None = None) -> datetime:
    base = from_time or utc_now()
    if frequency == "daily":
        return base + timedelta(days=1)
    elif frequency == "monthly":
        return base + timedelta(days=30)
    else:  # "weekly" default
        return base + timedelta(days=7)


def build_executive_html_email_content(
    report_type: str,
    sla_percentage: float,
    total_nodes: int,
    up_count: int,
    down_count: int,
    warn_count: int,
    recent_alerts: list[dict[str, Any]],
) -> str:
    """Renders a responsive HTML Executive Email Summary Template."""
    now_str = utc_now().strftime("%B %d, %Y - %H:%M UTC")

    alert_rows_html = ""
    for a in recent_alerts[:5]:
        sev_color = "#ef4444" if a.get("severity") == "critical" else "#f59e0b"
        alert_rows_html += f"""
        <tr>
          <td style="padding: 8px 12px; border-bottom: 1px solid #334155; color: {sev_color}; font-weight: bold;">{a.get("severity", "").upper()}</td>
          <td style="padding: 8px 12px; border-bottom: 1px solid #334155; color: #f8fafc;">{a.get("message", "")}</td>
          <td style="padding: 8px 12px; border-bottom: 1px solid #334155; color: #94a3b8;">{a.get("triggered_at", "")}</td>
        </tr>
        """

    if not alert_rows_html:
        alert_rows_html = """
        <tr>
          <td colspan="3" style="padding: 12px; text-align: center; color: #10b981;">✔ All systems operating within normal parameters. No recent critical incidents.</td>
        </tr>
        """

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="utf-8">
      <title>Executive Infrastructure Summary Report</title>
      <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #0f172a; color: #f8fafc; margin: 0; padding: 20px; }}
        .container {{ max-width: 680px; margin: 0 auto; background: #1e293b; border-radius: 8px; overflow: hidden; border: 1px solid #334155; }}
        .header {{ background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%); padding: 24px; border-bottom: 2px solid #3b82f6; }}
        .header h1 {{ margin: 0; font-size: 22px; color: #60a5fa; }}
        .header p {{ margin: 6px 0 0 0; font-size: 13px; color: #94a3b8; }}
        .body-content {{ padding: 24px; }}
        .kpi-grid {{ display: flex; gap: 12px; margin-bottom: 24px; }}
        .kpi-card {{ flex: 1; background: #0f172a; border: 1px solid #334155; border-radius: 6px; padding: 14px; text-align: center; }}
        .kpi-title {{ font-size: 11px; text-transform: uppercase; color: #94a3b8; letter-spacing: 0.5px; }}
        .kpi-value {{ font-size: 22px; font-weight: bold; margin-top: 4px; color: #f8fafc; }}
        .sla-green {{ color: #10b981; }}
        .table {{ width: 100%; border-collapse: collapse; margin-top: 12px; font-size: 13px; }}
        .table th {{ background: #0f172a; color: #94a3b8; text-align: left; padding: 8px 12px; border-bottom: 1px solid #334155; }}
        .footer {{ background: #0f172a; padding: 16px; text-align: center; font-size: 12px; color: #64748b; border-top: 1px solid #334155; }}
      </style>
    </head>
    <body>
      <div class="container">
        <div class="header">
          <h1>Executive Infrastructure Monitoring Report</h1>
          <p>Period: {report_type.capitalize()} Summary | Generated: {now_str}</p>
        </div>
        <div class="body-content">
          <div class="kpi-grid">
            <div class="kpi-card">
              <div class="kpi-title">Availability SLA</div>
              <div class="kpi-value sla-green">{sla_percentage:.2f}%</div>
            </div>
            <div class="kpi-card">
              <div class="kpi-title">Total Assets</div>
              <div class="kpi-value">{total_nodes}</div>
            </div>
            <div class="kpi-card">
              <div class="kpi-title">Nodes UP / DOWN</div>
              <div class="kpi-value">{up_count} / <span style="color:#ef4444">{down_count}</span></div>
            </div>
          </div>

          <h3 style="color: #60a5fa; margin-top: 20px; font-size: 15px;">Recent Critical Incident Summary</h3>
          <table class="table">
            <thead>
              <tr>
                <th>Severity</th>
                <th>Incident Description</th>
                <th>Timestamp</th>
              </tr>
            </thead>
            <tbody>
              {alert_rows_html}
            </tbody>
          </table>

          <p style="margin-top: 24px; font-size: 13px; color: #94a3b8;">
            Attachment Note: Detailed PDF and Excel audit workbooks have been attached to this email for full asset inventory and metric logs.
          </p>
        </div>
        <div class="footer">
          Auto-generated by Infrastructure Monitoring & Auto-Topology Engine. Confidential.
        </div>
      </div>
    </body>
    </html>
    """
    return html


async def send_executive_report_email(
    schedule: ReportSchedule,
    recipients: list[str],
    pdf_path: str | None = None,
    excel_path: str | None = None,
    html_content: str = "",
) -> bool:
    """Sends executive HTML email report with attached PDF/Excel files to recipients."""
    import os
    from services.alert_service import get_active_notification_provider

    provider = get_active_notification_provider()
    attachments = [p for p in (pdf_path, excel_path) if p and os.path.exists(p)]

    for email_addr in recipients:
        await provider.send_notification(
            title=f"[EXECUTIVE REPORT] {schedule.name}",
            message=f"Executive {schedule.report_type.capitalize()} Report delivered to {email_addr}.",
            severity="info",
            details={
                "recipient": email_addr,
                "schedule_id": str(schedule.id),
                "pdf_path": pdf_path,
                "excel_path": excel_path,
                "html_body_length": len(html_content),
            },
            attachments=attachments,
            html_body=html_content,
        )
    return True


async def execute_single_report_schedule(db: AsyncSession, schedule: ReportSchedule) -> bool:
    """Executes a single report schedule, generating reports and dispatching email."""
    now = utc_now()
    pdf_path = None
    excel_path = None

    # Fetch nodes & alerts for KPI summary
    nodes_res = await db.execute(select(Node))
    nodes = list(nodes_res.scalars().all())
    up_count = sum(1 for n in nodes if n.status == "up")
    down_count = sum(1 for n in nodes if n.status == "down")
    warn_count = sum(1 for n in nodes if n.status == "warning")
    total_nodes = len(nodes)
    sla_percentage = (up_count / total_nodes * 100) if total_nodes > 0 else 100.0

    alerts_res = await db.execute(select(Alert).order_by(Alert.triggered_at.desc()).limit(10))
    alerts = list(alerts_res.scalars().all())
    recent_alerts_data = [
        {"severity": a.severity, "message": a.message, "triggered_at": a.triggered_at.strftime("%Y-%m-%d %H:%M")}
        for a in alerts
    ]

    # Generate PDF if requested
    if schedule.export_format in ("pdf", "both"):
        _, pdf_path = await generate_pdf_report(db, report_type=schedule.report_type)

    # Generate Excel if requested
    if schedule.export_format in ("excel", "both"):
        _, excel_path = await generate_excel_report(db, report_type=schedule.report_type)

    # Build HTML email body
    html_content = build_executive_html_email_content(
        report_type=schedule.report_type,
        sla_percentage=sla_percentage,
        total_nodes=total_nodes,
        up_count=up_count,
        down_count=down_count,
        warn_count=warn_count,
        recent_alerts=recent_alerts_data,
    )

    recipients_list = schedule.recipients.get("emails", []) if isinstance(schedule.recipients, dict) else []
    if not recipients_list:
        logger.warning(f"Report schedule '{schedule.name}' has no recipients configured.")
        return False

    # Send Email
    await send_executive_report_email(
        schedule=schedule,
        recipients=recipients_list,
        pdf_path=pdf_path,
        excel_path=excel_path,
        html_content=html_content,
    )

    # Update Schedule timestamps
    schedule.last_run_at = now
    schedule.next_run_at = calculate_next_run_at(schedule.frequency, now)

    # Audit log
    audit = AuditLog(
        actor_username="system_cron_report_engine",
        action="SCHEDULED_REPORT_EXECUTED",
        target=str(schedule.id),
        metadata_={
            "schedule_name": schedule.name,
            "recipients_count": len(recipients_list),
            "export_format": schedule.export_format,
            "next_run_at": schedule.next_run_at.isoformat(),
        },
    )
    db.add(audit)
    await db.commit()
    await db.refresh(schedule)

    return True


async def execute_due_report_schedules(db: AsyncSession) -> list[ReportSchedule]:
    """Cron Engine runner that checks and executes due report schedules."""
    now = utc_now()
    stmt = select(ReportSchedule).where(
        ReportSchedule.is_enabled == True,
        (ReportSchedule.next_run_at == None) | (ReportSchedule.next_run_at <= now),
    )
    res = await db.execute(stmt)
    due_schedules = list(res.scalars().all())

    executed = []
    for sched in due_schedules:
        try:
            success = await execute_single_report_schedule(db, sched)
            if success:
                executed.append(sched)
        except Exception as err:
            logger.error(f"Failed executing report schedule '{sched.name}': {err}")

    return executed
