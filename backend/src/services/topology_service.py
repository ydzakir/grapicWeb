import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.node import LifecycleStatus, Node, NodeConnection, ReviewStatus
from schemas.node import TopologyEdgeResponse, TopologyGraphResponse, TopologyNodeResponse

# Keys to sanitize from presentation metadata
SENSITIVE_METADATA_KEYS = {
    "password",
    "secret",
    "private_key",
    "auth_token",
    "credentials",
    "credential_id",
}


def sanitize_metadata(metadata: dict[str, Any] | None) -> dict[str, Any]:
    if not metadata:
        return {}
    sanitized = {}
    for key, val in metadata.items():
        if key.lower() not in SENSITIVE_METADATA_KEYS and not key.lower().startswith("secret_"):
            sanitized[key] = val
    return sanitized


from models.network import NetworkEdge


async def build_topology_graph(
    db: AsyncSession,
    include_pending: bool = False,
    scope_datacenter_id: uuid.UUID | None = None,
    mode: str = "hierarchy",
) -> TopologyGraphResponse:
    """
    Build JSON topology graph with nodes and edges.
    - Filters: lifecycle_status == ACTIVE, review_status == APPROVED (unless include_pending=True).
    - Stable JSON node and edge structures.
    - Cycle defense: skips edges that introduce cycles.
    """
    # 1. Fetch eligible nodes
    node_query = select(Node).where(Node.lifecycle_status == LifecycleStatus.ACTIVE)
    if not include_pending:
        node_query = node_query.where(Node.review_status == ReviewStatus.APPROVED)

    res = await db.execute(node_query)
    all_nodes = list(res.scalars().all())
    node_map = {n.id: n for n in all_nodes}

    # If scoping to a specific Data Center, gather root DC node and all descendant nodes
    if scope_datacenter_id and scope_datacenter_id in node_map:
        scoped_ids: set[uuid.UUID] = {scope_datacenter_id}
        queue = [scope_datacenter_id]
        while queue:
            curr_id = queue.pop(0)
            for n in all_nodes:
                if n.parent_id == curr_id and n.id not in scoped_ids:
                    scoped_ids.add(n.id)
                    queue.append(n.id)
        node_map = {nid: node_map[nid] for nid in scoped_ids}

    # Build topology node responses
    nodes_response: list[TopologyNodeResponse] = []
    for node in node_map.values():
        nodes_response.append(
            TopologyNodeResponse(
                id=node.id,
                name=node.name,
                type=node.type,
                status=node.status,
                parent_id=node.parent_id,
                review_status=node.review_status,
                lifecycle_status=node.lifecycle_status,
                ip_address=node.ip_address,
                os=node.os,
                cpu_cores=node.cpu_cores,
                ram_mb=node.ram_mb,
                disk_gb=node.disk_gb,
                metadata=sanitize_metadata(node.metadata_),
            )
        )

    # 2. Build edges
    edges_response: list[TopologyEdgeResponse] = []
    edge_seen: set[tuple[str, str, str]] = set()

    # Implicit parent-child edges ("hosts" / hierarchy connection)
    for node in node_map.values():
        if node.parent_id and node.parent_id in node_map:
            source_id = str(node.parent_id)
            target_id = str(node.id)
            conn_type = "hosts"
            edge_key = (source_id, target_id, conn_type)

            if edge_key not in edge_seen and source_id != target_id:
                edge_seen.add(edge_key)
                edges_response.append(
                    TopologyEdgeResponse(
                        id=f"e-hosts-{source_id}-{target_id}",
                        source=source_id,
                        target=target_id,
                        connection_type=conn_type,
                        metadata={"label": "hosts"},
                    )
                )

    # Explicit Network Edge connections from DB (for Network mode & manual links)
    net_query = select(NetworkEdge)
    net_res = await db.execute(net_query)
    all_net_edges = list(net_res.scalars().all())

    for n_edge in all_net_edges:
        if n_edge.source_node_id in node_map and n_edge.target_node_id in node_map:
            source_id = str(n_edge.source_node_id)
            target_id = str(n_edge.target_node_id)
            conn_type = n_edge.connection_type
            edge_key = (source_id, target_id, conn_type)

            if edge_key not in edge_seen and source_id != target_id:
                edge_seen.add(edge_key)
                edges_response.append(
                    TopologyEdgeResponse(
                        id=f"e-net-{n_edge.id}",
                        source=source_id,
                        target=target_id,
                        connection_type=conn_type,
                        metadata={
                            "provenance": n_edge.provenance,
                            "confidence": n_edge.confidence_level.value if hasattr(n_edge.confidence_level, "value") else str(n_edge.confidence_level),
                            "has_active_traffic": n_edge.has_active_traffic,
                        },
                    )
                )

    return TopologyGraphResponse(nodes=nodes_response, edges=edges_response)
