from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_user, get_db
from core.cluster_ha import get_cluster_state
from models.user import User

router = APIRouter(prefix="/cluster", tags=["Cluster HA"])


@router.get("/status")
async def cluster_status(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return the current HA cluster state (leader, members, heartbeats)."""
    return await get_cluster_state(db)
