import uuid
from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_user, require_role, get_db
from models.user import User, UserRole
from schemas.node import TopologyGraphResponse
from services import topology_service
from services.network_discovery_service import create_manual_network_edge

require_admin_role = require_role([UserRole.ADMIN])
router = APIRouter(prefix="/topology", tags=["Topology"])


class ManualEdgeCreateRequest(BaseModel):
    source_node_id: uuid.UUID
    target_node_id: uuid.UUID
    connection_type: str = "manual_link"


@router.get("", response_model=TopologyGraphResponse)
async def get_topology(
    include_pending: bool = Query(
        False, description="Include pending review nodes in topology graph"
    ),
    datacenter_id: uuid.UUID | None = Query(
        None, description="Scope topology graph to a specific Data Center"
    ),
    mode: str = Query("hierarchy", description="Topology mode: 'hierarchy' or 'network'"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    graph = await topology_service.build_topology_graph(
        db=db,
        include_pending=include_pending,
        scope_datacenter_id=datacenter_id,
        mode=mode,
    )
    return graph


@router.post("/edges/manual", status_code=status.HTTP_201_CREATED)
async def create_manual_edge_endpoint(
    body: ManualEdgeCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin_role),
):
    """Create a manual fallback network edge mapping with audit trail (Admin only)."""
    edge = await create_manual_network_edge(
        db=db,
        source_node_id=body.source_node_id,
        target_node_id=body.target_node_id,
        connection_type=body.connection_type,
        username=current_user.username,
    )
    return {
        "id": str(edge.id),
        "source": str(edge.source_node_id),
        "target": str(edge.target_node_id),
        "connection_type": edge.connection_type,
        "provenance": edge.provenance,
        "confidence_level": edge.confidence_level.value,
    }
