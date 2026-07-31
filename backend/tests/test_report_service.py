import os
import pytest
import httpx
from httpx import AsyncClient
from main import app
from models.node import Node, NodeStatus
from models.user import User, UserRole
from core.security import create_access_token
from services.report_service import generate_pdf_report, generate_excel_report


@pytest.mark.asyncio
async def test_generate_pdf_and_excel_report_services(db_session):
    node = Node(
        name="SERVER-REPORT-TEST-01",
        type="physical_server",
        status=NodeStatus.UP,
        review_status="approved",
        lifecycle_status="active",
        cpu_cores=8,
        ram_mb=16384,
    )
    db_session.add(node)
    await db_session.commit()

    # Test PDF report generation
    pdf_name, pdf_path = await generate_pdf_report(db_session, report_type="weekly")
    assert os.path.exists(pdf_path)
    assert pdf_name.endswith(".pdf")
    assert os.path.getsize(pdf_path) > 0

    # Test Excel report generation
    excel_name, excel_path = await generate_excel_report(db_session, report_type="monthly")
    assert os.path.exists(excel_path)
    assert excel_name.endswith(".xlsx")
    assert os.path.getsize(excel_path) > 0


@pytest.mark.asyncio
async def test_report_api_generate_and_download(db_session):
    admin = User(
        username="admin_report_tester",
        email="report_admin@infra.com",
        hashed_password="hash",
        role=UserRole.ADMIN,
        is_active=True,
    )
    db_session.add(admin)
    await db_session.commit()

    token = create_access_token(subject=str(admin.id), role=admin.role.value)
    headers = {"Authorization": f"Bearer {token}"}

    async with AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
        # Generate PDF Report API
        post_resp = await ac.post(
            "/api/v1/reports/generate",
            json={"report_type": "weekly", "format": "pdf"},
            headers=headers,
        )
        assert post_resp.status_code == 201
        data = post_resp.json()
        assert "filename" in data
        assert data["download_url"].startswith("/api/v1/reports/download/")

        filename = data["filename"]

        # Download Report API
        dl_resp = await ac.get(f"/api/v1/reports/download/{filename}", headers=headers)
        assert dl_resp.status_code == 200
        assert dl_resp.headers["content-type"] == "application/pdf"
        assert len(dl_resp.content) > 0
