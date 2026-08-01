import pytest
from httpx import AsyncClient

from core.sso.ldap_driver import LdapAuthDriver
from core.sso.oidc_driver import OidcAuthDriver
from models.user import User, UserRole
from services.sso_service import auto_provision_sso_user, map_external_groups_to_user_role


@pytest.mark.asyncio
async def test_group_role_mapping():
    """Test mapping external LDAP/OIDC groups to internal UserRole."""
    assert map_external_groups_to_user_role(["Domain Admins"]) == UserRole.ADMIN
    assert map_external_groups_to_user_role(["Infra Ops"]) == UserRole.OPERATOR
    assert map_external_groups_to_user_role(["Regular Users"]) == UserRole.VIEWER
    assert map_external_groups_to_user_role([]) == UserRole.VIEWER


@pytest.mark.asyncio
async def test_ldap_auth_driver_simulation():
    """Test LdapAuthDriver simulated authentication."""
    driver = LdapAuthDriver()

    # Valid LDAP credential
    res = await driver.authenticate("ldapuser", "LdapSecurePass123!")
    assert res is not None
    assert res["username"] == "ldapuser"
    assert res["provider"] == "ldap"
    assert "Domain Admins" in res["groups"]

    # Invalid LDAP credential
    invalid_res = await driver.authenticate("ldapuser", "wrong_pass")
    assert invalid_res is None


@pytest.mark.asyncio
async def test_oidc_driver_and_auto_provision(db_session):
    """Test OIDC driver authorization URL and auto-provisioning service."""
    oidc = OidcAuthDriver()
    auth_data = oidc.get_authorization_url(state="nonce_123")
    assert "authorization_url" in auth_data
    assert auth_data["state"] == "nonce_123"

    # Simulate callback
    user_info = await oidc.handle_callback("mock_code_xyz")
    assert user_info is not None

    # Auto provision user in DB
    user = await auto_provision_sso_user(db_session, user_info)
    assert user.id is not None
    assert user.role == UserRole.OPERATOR
    assert user.is_active is True


@pytest.mark.asyncio
async def test_sso_api_endpoints(async_client: AsyncClient, db_session):
    """Test REST API endpoints GET /auth/providers, POST /auth/ldap/login, GET /auth/oidc/authorize."""
    # 1. GET /api/v1/auth/providers
    prov_resp = await async_client.get("/api/v1/auth/providers")
    assert prov_resp.status_code == 200
    data = prov_resp.json()
    assert "local" in data["providers"]
    assert "ldap" in data["providers"]
    assert "oidc" in data["providers"]

    # 2. POST /api/v1/auth/ldap/login
    ldap_resp = await async_client.post(
        "/api/v1/auth/ldap/login",
        json={"username": "ldapuser", "password": "LdapSecurePass123!"},
    )
    assert ldap_resp.status_code == 200, ldap_resp.text
    token_data = ldap_resp.json()
    assert "access_token" in token_data
    assert token_data["user"]["username"] == "ldapuser"

    # 3. GET /api/v1/auth/oidc/authorize
    oidc_resp = await async_client.get("/api/v1/auth/oidc/authorize")
    assert oidc_resp.status_code == 200
    assert "authorization_url" in oidc_resp.json()

    # 4. POST /api/v1/auth/oidc/callback
    cb_resp = await async_client.post(
        "/api/v1/auth/oidc/callback",
        json={"code": "mock_code_123"},
    )
    assert cb_resp.status_code == 200, cb_resp.text
    assert "access_token" in cb_resp.json()
