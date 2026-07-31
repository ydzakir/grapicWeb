import uuid
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_user, require_role, get_db
from models.user import User, UserRole
from models.topology_history import TopologySnapshot
from schemas.node import TopologyGraphResponse
from services import topology_service
from services.network_discovery_service import create_manual_network_edge
from services.topology_history_service import (
    save_topology_snapshot,
    get_topology_snapshots,
    compare_topology_graphs,
)

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


@router.post("/snapshots/take", status_code=status.HTTP_201_CREATED)
async def take_topology_snapshot(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin_role),
):
    """Save a versioned snapshot of the current topology graph."""
    current_graph = await topology_service.build_topology_graph(db=db, include_pending=True)
    graph_dict = current_graph.model_dump(mode="json")
    snapshot = await save_topology_snapshot(db=db, graph_data=graph_dict)
    return {
        "snapshot_id": str(snapshot.id),
        "timestamp": snapshot.timestamp,
        "node_count": snapshot.node_count,
        "edge_count": snapshot.edge_count,
    }


@router.get("/snapshots")
async def list_topology_snapshots(
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List historical topology snapshots for time-travel selection."""
    snapshots = await get_topology_snapshots(db=db, limit=limit)
    return [
        {
            "id": str(s.id),
            "timestamp": s.timestamp,
            "node_count": s.node_count,
            "edge_count": s.edge_count,
        }
        for s in snapshots
    ]


@router.get("/compare")
async def compare_topology_snapshots_endpoint(
    snapshot_a_id: uuid.UUID,
    snapshot_b_id: Optional[uuid.UUID] = Query(None, description="Snapshot B ID (or current if omitted)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Compare two topology graph snapshots (Time-Travel comparison diff)."""
    snap_a = await db.get(TopologySnapshot, snapshot_a_id)
    if not snap_a:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Snapshot A not found")

    if snapshot_b_id:
        snap_b = await db.get(TopologySnapshot, snapshot_b_id)
        if not snap_b:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Snapshot B not found")
        graph_b = snap_b.graph_json
    else:
        current_g = await topology_service.build_topology_graph(db=db, include_pending=True)
        graph_b = current_g.model_dump(mode="json")

    diff = compare_topology_graphs(old_graph=snap_a.graph_json, new_graph=graph_b)
    return diff
