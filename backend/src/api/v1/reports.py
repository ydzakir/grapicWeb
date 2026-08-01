import os
import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_user, get_db, require_role
from models.report_schedule import ReportSchedule
from models.user import User, UserRole
from schemas.report_schedule import (
    ReportScheduleCreate,
    ReportScheduleResponse,
    ReportScheduleUpdate,
)
from services.report_scheduler_service import (
    calculate_next_run_at,
    execute_single_report_schedule,
    utc_now,
)
from services.report_service import REPORTS_DIR, generate_excel_report, generate_pdf_report

require_admin_role = require_role([UserRole.ADMIN])

router = APIRouter(prefix="/reports", tags=["Reports"])


class ReportGenerateRequest(BaseModel):
    report_type: str = "weekly" # weekly, monthly
    format: str = "pdf"         # pdf, excel


@router.post("/generate", status_code=status.HTTP_201_CREATED)
async def generate_report_endpoint(
    body: ReportGenerateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate Executive Report PDF or Excel File."""
    fmt = body.format.lower()
    rtype = body.report_type.lower()

    if fmt == "excel":
        filename, filepath = await generate_excel_report(db, report_type=rtype)
    else:
        filename, filepath = await generate_pdf_report(db, report_type=rtype)

    return {
        "filename": filename,
        "download_url": f"/api/v1/reports/download/{filename}",
        "report_type": rtype,
        "format": fmt,
    }


@router.get("/download/{filename}")
async def download_report_file(
    filename: str,
    current_user: User = Depends(get_current_user),
):
    """Download generated report document."""
    filepath = os.path.join(REPORTS_DIR, filename)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report file not found")

    media_type = "application/pdf" if filename.endswith(".pdf") else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    return FileResponse(
        path=filepath,
        filename=filename,
        media_type=media_type,
    )


# --- REPORT SCHEDULE ENDPOINTS ---

@router.get("/schedules", response_model=List[ReportScheduleResponse])
async def list_report_schedules(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all configured automated report schedules."""
    stmt = select(ReportSchedule).order_by(desc(ReportSchedule.created_at))
    res = await db.execute(stmt)
    schedules = list(res.scalars().all())

    response_list = []
    for s in schedules:
        rec_list = s.recipients.get("emails", []) if isinstance(s.recipients, dict) else []
        response_list.append(
            ReportScheduleResponse(
                id=s.id,
                name=s.name,
                frequency=s.frequency,
                report_type=s.report_type,
                export_format=s.export_format,
                recipients=rec_list,
                is_enabled=s.is_enabled,
                last_run_at=s.last_run_at,
                next_run_at=s.next_run_at,
                created_at=s.created_at,
            )
        )
    return response_list


@router.post("/schedules", response_model=ReportScheduleResponse, status_code=status.HTTP_201_CREATED)
async def create_report_schedule(
    body: ReportScheduleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin_role),
):
    """Create a new automated report delivery schedule (Admin only)."""
    now = utc_now()
    next_run = calculate_next_run_at(body.frequency, now)

    schedule = ReportSchedule(
        name=body.name,
        frequency=body.frequency,
        report_type=body.report_type,
        export_format=body.export_format,
        recipients={"emails": body.recipients},
        is_enabled=body.is_enabled,
        next_run_at=next_run,
    )
    db.add(schedule)
    await db.commit()
    await db.refresh(schedule)

    return ReportScheduleResponse(
        id=schedule.id,
        name=schedule.name,
        frequency=schedule.frequency,
        report_type=schedule.report_type,
        export_format=schedule.export_format,
        recipients=body.recipients,
        is_enabled=schedule.is_enabled,
        last_run_at=schedule.last_run_at,
        next_run_at=schedule.next_run_at,
        created_at=schedule.created_at,
    )


@router.post("/schedules/{schedule_id}/trigger", response_model=ReportScheduleResponse)
async def trigger_report_schedule_endpoint(
    schedule_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin_role),
):
    """Manually trigger immediate execution of an automated report schedule (Admin only)."""
    schedule = await db.get(ReportSchedule, schedule_id)
    if not schedule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report schedule not found")

    await execute_single_report_schedule(db, schedule)
    await db.refresh(schedule)

    rec_list = schedule.recipients.get("emails", []) if isinstance(schedule.recipients, dict) else []
    return ReportScheduleResponse(
        id=schedule.id,
        name=schedule.name,
        frequency=schedule.frequency,
        report_type=schedule.report_type,
        export_format=schedule.export_format,
        recipients=rec_list,
        is_enabled=schedule.is_enabled,
        last_run_at=schedule.last_run_at,
        next_run_at=schedule.next_run_at,
        created_at=schedule.created_at,
    )


@router.delete("/schedules/{schedule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_report_schedule(
    schedule_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin_role),
):
    """Delete a report schedule rule (Admin only)."""
    schedule = await db.get(ReportSchedule, schedule_id)
    if not schedule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report schedule not found")

    await db.delete(schedule)
    await db.commit()
    return None
