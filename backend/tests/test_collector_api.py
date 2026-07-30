import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from core.security import create_access_token, get_password_hash
from models.user import User, UserRole


@pytest.mark.asyncio
async def test_admin_collector_target_crud(db_session: AsyncSession, async_client: AsyncClient):
    admin = User(
        username="admin_collector",
        email="admin_col@infra.com",
        hashed_password=get_password_hash("AdminPass123!"),
        role=UserRole.ADMIN,
    )
    db_session.add(admin)
    await db_session.commit()

    token = create_access_token(subject=str(admin.id), role=admin.role.value)
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Create Collector Target (Valid interval 60s)
    payload = {
        "name": "Production Web Cluster",
        "target_type": "ssh",
        "host": "192.168.1.10",
        "port": 22,
        "credential_reference": "docker_secret:ssh_web_key",
        "poll_interval_seconds": 60,
    }

    response = await async_client.post("/api/v1/collectors", json=payload, headers=headers)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Production Web Cluster"
    assert data["credential_reference"] == "docker_secret:ssh_web_key"
    target_id = data["id"]

    # 2. List Collector Targets
    list_resp = await async_client.get("/api/v1/collectors", headers=headers)
    assert list_resp.status_code == 200
    assert len(list_resp.json()) >= 1

    # 3. Get Collector Target
    get_resp = await async_client.get(f"/api/v1/collectors/{target_id}", headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == target_id

    # 4. Test Connection
    test_resp = await async_client.post(
        f"/api/v1/collectors/{target_id}/test-connection", headers=headers
    )
    assert test_resp.status_code == 200
    test_data = test_resp.json()
    assert test_data["target_id"] == target_id
    assert "success" in test_data

    # 5. Delete Collector Target
    del_resp = await async_client.delete(f"/api/v1/collectors/{target_id}", headers=headers)
    assert del_resp.status_code == 204


@pytest.mark.asyncio
async def test_operator_and_viewer_rejected_from_collector_crud(
    db_session: AsyncSession, async_client: AsyncClient
):
    operator = User(
        username="op_user",
        email="operator@infra.com",
        hashed_password=get_password_hash("OpPass123!"),
        role=UserRole.OPERATOR,
    )
    db_session.add(operator)
    await db_session.commit()

    token = create_access_token(subject=str(operator.id), role=operator.role.value)
    headers = {"Authorization": f"Bearer {token}"}

    response = await async_client.get("/api/v1/collectors", headers=headers)
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


@pytest.mark.asyncio
async def test_invalid_poll_interval_rejected(db_session: AsyncSession, async_client: AsyncClient):
    admin = User(
        username="admin_interval",
        email="admin_interval@infra.com",
        hashed_password=get_password_hash("AdminPass123!"),
        role=UserRole.ADMIN,
    )
    db_session.add(admin)
    await db_session.commit()

    token = create_access_token(subject=str(admin.id), role=admin.role.value)
    headers = {"Authorization": f"Bearer {token}"}

    # Interval < 30s must be rejected (422)
    payload_too_low = {
        "name": "Invalid Low Target",
        "target_type": "ssh",
        "host": "192.168.1.15",
        "port": 22,
        "credential_reference": "ref",
        "poll_interval_seconds": 15,
    }
    res_low = await async_client.post("/api/v1/collectors", json=payload_too_low, headers=headers)
    assert res_low.status_code == 422

    # Interval > 60s must be rejected (422)
    payload_too_high = {
        "name": "Invalid High Target",
        "target_type": "ssh",
        "host": "192.168.1.15",
        "port": 22,
        "credential_reference": "ref",
        "poll_interval_seconds": 120,
    }
    res_high = await async_client.post("/api/v1/collectors", json=payload_too_high, headers=headers)
    assert res_high.status_code == 422
