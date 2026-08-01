"""Tests for the honest minimal HA cluster support (leader election + status API)."""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from core.cluster_ha import (
    _is_leader,
    cluster_leader_cycle,
    generate_node_id,
    get_cluster_state,
)
from core.security import create_access_token
from models.user import User, UserRole


@pytest.mark.asyncio
async def test_cluster_leader_cycle_single_node(db_session: AsyncSession):
    """In single-node/non-PG mode the process becomes leader and heartbeats."""
    is_leader = await cluster_leader_cycle(db_session)
    assert is_leader is True

    state = await get_cluster_state(db_session)
    assert state["ha_mode_enabled"] is False
    assert state["members"] is not None


@pytest.mark.asyncio
async def test_cluster_status_api_authenticated(async_client: AsyncClient, db_session: AsyncSession):
    admin = User(
        username="cluster_admin",
        email="cluster@infra.com",
        hashed_password="hash",
        role=UserRole.ADMIN,
        is_active=True,
    )
    db_session.add(admin)
    await db_session.commit()
    token = create_access_token(subject=str(admin.id), role=admin.role.value)
    headers = {"Authorization": f"Bearer {token}"}

    resp = await async_client.get("/api/v1/cluster/status", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert "members" in body
    assert "current_node_id" in body
    assert "am_i_leader" in body


def test_cluster_node_id_generator():
    node_id = generate_node_id()
    assert node_id.startswith("backend-")
    assert len(node_id.split("-")) >= 2
