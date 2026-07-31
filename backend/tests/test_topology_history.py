import pytest
import httpx
from httpx import AsyncClient
from main import app
from models.node import Node, NodeStatus
from models.user import User, UserRole
from core.security import create_access_token
from services.topology_history_service import (
    save_topology_snapshot,
    get_topology_snapshots,
    compare_topology_graphs,
)


@pytest.mark.asyncio
async def test_topology_snapshot_save_and_diff_comparison(db_session):
    node1 = Node(name="NODE-SNAPSHOT-01", type="physical_server", status=NodeStatus.UP, review_status="approved", lifecycle_status="active")
    db_session.add(node1)
    await db_session.commit()

    graph_v1 = {"nodes": [{"id": str(node1.id), "name": "NODE-SNAPSHOT-01", "status": "up"}], "edges": []}
    snap1 = await save_topology_snapshot(db_session, graph_v1)
    assert snap1.node_count == 1

    # Add second node for v2
    node2 = Node(name="NODE-SNAPSHOT-02", type="physical_server", status=NodeStatus.UP, review_status="approved", lifecycle_status="active")
    db_session.add(node2)
    await db_session.commit()

    graph_v2 = {
        "nodes": [
            {"id": str(node1.id), "name": "NODE-SNAPSHOT-01", "status": "up"},
            {"id": str(node2.id), "name": "NODE-SNAPSHOT-02", "status": "up"},
        ],
        "edges": [{"id": "e1", "source": str(node1.id), "target": str(node2.id)}],
    }
    snap2 = await save_topology_snapshot(db_session, graph_v2)
    assert snap2.node_count == 2

    # Compare v1 vs v2
    diff = compare_topology_graphs(snap1.graph_json, snap2.graph_json)
    assert len(diff["added_nodes"]) == 1
    assert diff["added_nodes"][0]["name"] == "NODE-SNAPSHOT-02"
    assert len(diff["added_edges"]) == 1
    assert diff["summary"]["changes_detected"] is True


@pytest.mark.asyncio
async def test_topology_history_api_endpoints(db_session):
    admin = User(
        username="admin_history_tester",
        email="history_admin@infra.com",
        hashed_password="hash",
        role=UserRole.ADMIN,
        is_active=True,
    )
    db_session.add(admin)
    await db_session.commit()

    token = create_access_token(subject=str(admin.id), role=admin.role.value)
    headers = {"Authorization": f"Bearer {token}"}

    async with AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
        # Take Snapshot API
        take_resp = await ac.post("/api/v1/topology/snapshots/take", headers=headers)
        assert take_resp.status_code == 201
        data = take_resp.json()
        assert "snapshot_id" in data
        snap_id = data["snapshot_id"]

        # List Snapshots API
        list_resp = await ac.get("/api/v1/topology/snapshots", headers=headers)
        assert list_resp.status_code == 200
        snaps = list_resp.json()
        assert len(snaps) >= 1

        # Compare API
        comp_resp = await ac.get(f"/api/v1/topology/compare?snapshot_a_id={snap_id}", headers=headers)
        assert comp_resp.status_code == 200
        diff = comp_resp.json()
        assert "added_nodes" in diff
