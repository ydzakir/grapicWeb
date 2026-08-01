import pytest
from datetime import datetime, timezone
from httpx import AsyncClient

from core.security import create_access_token
from models.report_schedule import ReportSchedule
from models.user import User, UserRole
from services.report_scheduler_service import (
    build_executive_html_email_content,
    calculate_next_run_at,
    execute_single_report_schedule,
)


@pytest.mark.asyncio
async def test_calculate_next_run_at():
    now = datetime(2026, 8, 1, 12, 0, 0, tzinfo=timezone.utc)
    next_daily = calculate_next_run_at("daily", now)
    assert next_daily == datetime(2026, 8, 2, 12, 0, 0, tzinfo=timezone.utc)

    next_weekly = calculate_next_run_at("weekly", now)
    assert next_weekly == datetime(2026, 8, 8, 12, 0, 0, tzinfo=timezone.utc)

    next_monthly = calculate_next_run_at("monthly", now)
    assert next_monthly == datetime(2026, 8, 31, 12, 0, 0, tzinfo=timezone.utc)


@pytest.mark.asyncio
async def test_html_email_template_rendering():
    html = build_executive_html_email_content(
        report_type="weekly",
        sla_percentage=99.95,
        total_nodes=25,
        up_count=24,
        down_count=1,
        warn_count=0,
        recent_alerts=[{"severity": "critical", "message": "High CPU 99%", "triggered_at": "2026-08-01 12:00"}],
    )
    assert "99.95%" in html
    assert "Executive Infrastructure Monitoring Report" in html
    assert "High CPU 99%" in html


@pytest.mark.asyncio
async def test_report_schedule_api_endpoints(async_client: AsyncClient, db_session):
    admin = User(
        username="admin_report_sched",
        email="admin_sched@infra.com",
        hashed_password="hash",
        role=UserRole.ADMIN,
        is_active=True,
    )
    db_session.add(admin)
    await db_session.commit()
    token = create_access_token(subject=str(admin.id), role=admin.role.value)
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Create Report Schedule
    create_resp = await async_client.post(
        "/api/v1/reports/schedules",
        json={
            "name": "Weekly Executive Uptime Report",
            "frequency": "weekly",
            "report_type": "weekly",
            "export_format": "pdf",
            "recipients": ["exec@company.com", "ops@company.com"],
            "is_enabled": True,
        },
        headers=headers,
    )
    assert create_resp.status_code == 201, create_resp.text
    sched_data = create_resp.json()
    schedule_id = sched_data["id"]
    assert sched_data["name"] == "Weekly Executive Uptime Report"
    assert "exec@company.com" in sched_data["recipients"]

    # 2. List Report Schedules
    list_resp = await async_client.get("/api/v1/reports/schedules", headers=headers)
    assert list_resp.status_code == 200
    assert len(list_resp.json()) >= 1

    # 3. Trigger Report Schedule manually
    trig_resp = await async_client.post(
        f"/api/v1/reports/schedules/{schedule_id}/trigger",
        headers=headers,
    )
    assert trig_resp.status_code == 200, trig_resp.text
    assert trig_resp.json()["last_run_at"] is not None

    # 4. Delete Report Schedule
    del_resp = await async_client.delete(
        f"/api/v1/reports/schedules/{schedule_id}",
        headers=headers,
    )
    assert del_resp.status_code == 204
