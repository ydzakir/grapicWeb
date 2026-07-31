from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from services.cloudflare_service import (
    get_cloudflare_edge_status,
    sync_cloudflare_and_evaluate_alerts,
)

router = APIRouter(prefix="/cloudflare", tags=["Cloudflare Edge Status"])


@router.get("/status")
async def get_status():
    """Get real-time global status summary of Cloudflare Edge Services."""
    summary = await get_cloudflare_edge_status()
    return {
        "status": "success",
        "data": summary.model_dump(),
    }


@router.post("/sync")
async def sync_status(db: AsyncSession = Depends(get_db)):
    """Trigger immediate sync scan of Cloudflare Edge and evaluate alert rules."""
    summary = await sync_cloudflare_and_evaluate_alerts(db)
    return {
        "status": "success",
        "message": "Cloudflare Edge status synced successfully",
        "data": summary.model_dump(),
    }


@router.get("/incidents")
async def get_incidents():
    """Get active Cloudflare Edge incident list."""
    summary = await get_cloudflare_edge_status()
    return {
        "status": "success",
        "total": len(summary.incidents),
        "data": [inc.model_dump() for inc in summary.incidents],
    }
