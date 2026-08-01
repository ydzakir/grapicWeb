import pytest
from httpx import AsyncClient

from core.security import create_access_token
from models.user import User, UserRole


@pytest.mark.asyncio
async def test_permissions_matrix_endpoint(async_client: AsyncClient, db_session):
    user = User(
        username="matrix_user",
        email="matrix@infra.com",
        hashed_password="hash",
        role=UserRole.VIEWER,
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    token = create_access_token(subject=str(user.id), role=user.role.value)
    headers = {"Authorization": f"Bearer {token}"}

    res = await async_client.get("/api/v1/users/permissions/matrix", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert "available_permissions" in data
    assert len(data["available_permissions"]) >= 5


@pytest.mark.asyncio
async def test_user_management_crud(async_client: AsyncClient, db_session):
    admin = User(
        username="admin_rbac_crud",
        email="admin_rbac@infra.com",
        hashed_password="hash",
        role=UserRole.ADMIN,
        is_active=True,
    )
    db_session.add(admin)
    await db_session.commit()
    token = create_access_token(subject=str(admin.id), role=admin.role.value)
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Create User with Granular Permissions and Scopes
    create_resp = await async_client.post(
        "/api/v1/users",
        json={
            "username": "operator_jkt",
            "email": "op_jkt@company.com",
            "password": "SecureOperatorPass123!",
            "role": "operator",
            "custom_permissions": ["nodes:read", "nodes:write", "topology:edit"],
            "allowed_group_scopes": ["Jakarta-DC", "Bandung-DC"],
            "is_active": True,
        },
        headers=headers,
    )
    assert create_resp.status_code == 201, create_resp.text
    user_data = create_resp.json()
    new_user_id = user_data["id"]
    assert user_data["username"] == "operator_jkt"
    assert "nodes:write" in user_data["custom_permissions"]["permissions"]
    assert "Jakarta-DC" in user_data["allowed_group_scopes"]["scopes"]

    # 2. List Users
    list_resp = await async_client.get("/api/v1/users", headers=headers)
    assert list_resp.status_code == 200
    assert len(list_resp.json()) >= 2

    # 3. Update User
    update_resp = await async_client.put(
        f"/api/v1/users/{new_user_id}",
        json={
            "custom_permissions": ["nodes:read", "nodes:write", "topology:edit", "reports:export"],
            "allowed_group_scopes": ["*"],
        },
        headers=headers,
    )
    assert update_resp.status_code == 200
    assert "reports:export" in update_resp.json()["custom_permissions"]["permissions"]
    assert "*" in update_resp.json()["allowed_group_scopes"]["scopes"]

    # 4. Delete User
    del_resp = await async_client.delete(f"/api/v1/users/{new_user_id}", headers=headers)
    assert del_resp.status_code == 204


@pytest.mark.asyncio
async def test_non_admin_forbidden_access(async_client: AsyncClient, db_session):
    viewer = User(
        username="viewer_user",
        email="viewer@infra.com",
        hashed_password="hash",
        role=UserRole.VIEWER,
        is_active=True,
    )
    db_session.add(viewer)
    await db_session.commit()
    token = create_access_token(subject=str(viewer.id), role=viewer.role.value)
    headers = {"Authorization": f"Bearer {token}"}

    # Attempt admin-only user creation -> Expected HTTP 403 Forbidden
    create_resp = await async_client.post(
        "/api/v1/users",
        json={
            "username": "hacker_user",
            "email": "hack@company.com",
            "password": "pass",
            "role": "admin",
        },
        headers=headers,
    )
    assert create_resp.status_code == 403
