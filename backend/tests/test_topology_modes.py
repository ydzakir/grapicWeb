import pytest
import httpx
from httpx import AsyncClient
from main import app
from models.node import Node, NodeStatus
from models.user import User, UserRole
from core.security import create_access_token
from services.network_discovery_service import create_manual_network_edge


@pytest.mark.asyncio
async def test_topology_modes_and_manual_edge_api(db_session):
    admin = User(
        username="topo_mode_admin",
        email="topo_mode_admin@infra.com",
        hashed_password="hash",
        role=UserRole.ADMIN,
        is_active=True,
    )
    db_session.add(admin)
    await db_session.commit()

    token = create_access_token(subject=str(admin.id), role=admin.role.value)
    headers = {"Authorization": f"Bearer {token}"}

    n1 = Node(name="HOST-MODE-01", type="physical_server", status=NodeStatus.UP, review_status="approved", lifecycle_status="active")
    n2 = Node(name="HOST-MODE-02", type="physical_server", status=NodeStatus.UP, review_status="approved", lifecycle_status="active")
    db_session.add_all([n1, n2])
    await db_session.commit()

    await create_manual_network_edge(
        db=db_session,
        source_node_id=n1.id,
        target_node_id=n2.id,
        connection_type="backbone_link",
        username=admin.username,
    )

    async with AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
        # Hierarchy mode query
        resp_h = await ac.get("/api/v1/topology?mode=hierarchy", headers=headers)
        assert resp_h.status_code == 200
        assert "nodes" in resp_h.json()

        # Network mode query
        resp_n = await ac.get("/api/v1/topology?mode=network", headers=headers)
        assert resp_n.status_code == 200
        net_edges = resp_n.json()["edges"]
        assert len(net_edges) >= 1
        assert any(e["connection_type"] == "backbone_link" for e in net_edges)

        # POST Manual Edge API
        n3 = Node(name="HOST-MODE-03", type="physical_server", status=NodeStatus.UP, review_status="approved", lifecycle_status="active")
        db_session.add(n3)
        await db_session.commit()

        post_resp = await ac.post(
            "/api/v1/topology/edges/manual",
            json={
                "source_node_id": str(n2.id),
                "target_node_id": str(n3.id),
                "connection_type": "manual_fiber",
            },
            headers=headers,
        )
        assert post_resp.status_code == 201
        assert post_resp.json()["provenance"] == "manual_user_defined"
