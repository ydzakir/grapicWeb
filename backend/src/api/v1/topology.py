import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_user, get_db
from models.user import User
from schemas.node import TopologyGraphResponse
from services import topology_service

router = APIRouter(prefix="/topology", tags=["Topology"])


@router.get("", response_model=TopologyGraphResponse)
async def get_topology(
    include_pending: bool = Query(
        False, description="Include pending review nodes in topology graph"
    ),
    datacenter_id: uuid.UUID | None = Query(
        None, description="Scope topology graph to a specific Data Center"
    ),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    graph = await topology_service.build_topology_graph(
        db=db,
        include_pending=include_pending,
        scope_datacenter_id=datacenter_id,
    )
    return graph
