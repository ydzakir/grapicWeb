import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.audit import sanitize_metadata
from core.security import create_access_token, get_password_hash
from models.user import User, UserRole
from services.auth_service import bootstrap_admin_user


@pytest.mark.asyncio
async def test_admin_bootstrap_idempotency(db_session: AsyncSession):
    # First run creates admin
    admin1 = await bootstrap_admin_user(db_session)
    await db_session.flush()
    assert admin1.role == UserRole.ADMIN
    assert admin1.username == "admin"

    # Second run returns same admin without creating duplicate
    admin2 = await bootstrap_admin_user(db_session)
    assert admin1.id == admin2.id

    stmt = select(User).where(User.role == UserRole.ADMIN)
    result = await db_session.execute(stmt)
    admins = result.scalars().all()
    assert len(admins) == 1


@pytest.mark.asyncio
async def test_login_success_and_cookie(db_session: AsyncSession, async_client: AsyncClient):
    user = User(
        username="john_operator",
        email="john@infra.com",
        hashed_password=get_password_hash("SecretPassword123!"),
        role=UserRole.OPERATOR,
    )
    db_session.add(user)
    await db_session.commit()

    response = await async_client.post(
        "/api/v1/auth/login",
        json={"username_or_email": "john_operator", "password": "SecretPassword123!"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["user"]["username"] == "john_operator"
    assert data["user"]["role"] == "operator"

    # Check HttpOnly cookie set
    assert "access_token" in response.cookies


@pytest.mark.asyncio
async def test_login_failure_invalid_password(db_session: AsyncSession, async_client: AsyncClient):
    user = User(
        username="janedoe",
        email="jane@infra.com",
        hashed_password=get_password_hash("CorrectPassword123!"),
        role=UserRole.VIEWER,
    )
    db_session.add(user)
    await db_session.commit()

    response = await async_client.post(
        "/api/v1/auth/login",
        json={"username_or_email": "janedoe", "password": "WrongPassword!"},
    )
    assert response.status_code == 401
    data = response.json()
    assert data["error"]["code"] == "INVALID_CREDENTIALS"


@pytest.mark.asyncio
async def test_protected_route_unauthorized(async_client: AsyncClient):
    response = await async_client.get("/api/v1/auth/me")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


@pytest.mark.asyncio
async def test_protected_route_authorized(db_session: AsyncSession, async_client: AsyncClient):
    user = User(
        username="active_user",
        email="active@infra.com",
        hashed_password=get_password_hash("Pass123!"),
        role=UserRole.VIEWER,
    )
    db_session.add(user)
    await db_session.commit()

    token = create_access_token(subject=str(user.id), role=user.role.value)
    headers = {"Authorization": f"Bearer {token}"}

    response = await async_client.get("/api/v1/auth/me", headers=headers)
    assert response.status_code == 200
    assert response.json()["username"] == "active_user"


def test_audit_metadata_sanitization():
    raw_metadata = {
        "user": "admin",
        "password": "SuperSecretPassword!",
        "access_token": "bearer eyJhbGciOi...",
        "nested": {
            "private_key": "---BEGIN RSA PRIVATE KEY---",
            "safe_field": "visible_data",
        },
    }
    clean = sanitize_metadata(raw_metadata)
    assert clean["password"] == "[REDACTED]"
    assert clean["access_token"] == "[REDACTED]"
    assert clean["nested"]["private_key"] == "[REDACTED]"
    assert clean["nested"]["safe_field"] == "visible_data"
