import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from models.topology_history import TopologySnapshot, TopologyChangeLog
from schemas.node import TopologyGraphResponse


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


async def save_topology_snapshot(db: AsyncSession, graph_data: Dict[str, Any]) -> TopologySnapshot:
    """
    Saves a snapshot of current topology graph for versioning & time-travel comparison.
    """
    nodes = graph_data.get("nodes", [])
    edges = graph_data.get("edges", [])

    snapshot = TopologySnapshot(
        timestamp=utc_now(),
        node_count=len(nodes),
        edge_count=len(edges),
        graph_json=graph_data,
    )
    db.add(snapshot)
    await db.commit()
    await db.refresh(snapshot)
    return snapshot


async def get_topology_snapshots(db: AsyncSession, limit: int = 50) -> List[TopologySnapshot]:
    """Retrieve historical topology snapshots."""
    stmt = select(TopologySnapshot).order_by(desc(TopologySnapshot.timestamp)).limit(limit)
    res = await db.execute(stmt)
    return list(res.scalars().all())


def compare_topology_graphs(old_graph: Dict[str, Any], new_graph: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compares two topology graph JSON structures (old vs new) and returns diff of added/removed/modified nodes & edges.
    """
    old_nodes_map = {str(n["id"]): n for n in old_graph.get("nodes", [])}
    new_nodes_map = {str(n["id"]): n for n in new_graph.get("nodes", [])}

    old_edges_map = {str(e["id"]): e for e in old_graph.get("edges", [])}
    new_edges_map = {str(e["id"]): e for e in new_graph.get("edges", [])}

    added_nodes = [new_nodes_map[nid] for nid in new_nodes_map if nid not in old_nodes_map]
    removed_nodes = [old_nodes_map[nid] for nid in old_nodes_map if nid not in new_nodes_map]

    modified_nodes = []
    for nid in new_nodes_map:
        if nid in old_nodes_map:
            old_n = old_nodes_map[nid]
            new_n = new_nodes_map[nid]
            if old_n.get("status") != new_n.get("status") or old_n.get("name") != new_n.get("name"):
                modified_nodes.append({"old": old_n, "new": new_n})

    added_edges = [new_edges_map[eid] for eid in new_edges_map if eid not in old_edges_map]
    removed_edges = [old_edges_map[eid] for eid in old_edges_map if eid not in new_edges_map]

    return {
        "added_nodes": added_nodes,
        "removed_nodes": removed_nodes,
        "modified_nodes": modified_nodes,
        "added_edges": added_edges,
        "removed_edges": removed_edges,
        "summary": {
            "nodes_delta": len(new_nodes_map) - len(old_nodes_map),
            "edges_delta": len(new_edges_map) - len(old_edges_map),
            "changes_detected": len(added_nodes) + len(removed_nodes) + len(modified_nodes) + len(added_edges) + len(removed_edges) > 0,
        },
    }
