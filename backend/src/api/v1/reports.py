import os
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_user, get_db
from models.user import User
from services.report_service import REPORTS_DIR, generate_excel_report, generate_pdf_report

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
