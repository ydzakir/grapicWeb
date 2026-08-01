import os
import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient

from core.security import create_access_token
from core.secrets import HashiCorpVaultSecretProvider, EnvironmentAndFileSecretProvider
from core.vault_client import HashiCorpVaultClient
from models.user import User, UserRole


@pytest.mark.asyncio
async def test_vault_fallback_provider(monkeypatch):
    """Test automatic fallback from Vault to Environment variables if secret is unencrypted."""
    monkeypatch.setenv("TEST_CREDENTIAL_KEY", "super_secret_password_123")

    provider = HashiCorpVaultSecretProvider()
    val = provider.get_secret("TEST_CREDENTIAL_KEY")
    assert val == "super_secret_password_123"


@pytest.mark.asyncio
async def test_vault_client_mock_encrypt_decrypt():
    """Test HashiCorpVaultClient encrypt and decrypt methods with mocked HTTP responses."""
    client = HashiCorpVaultClient(vault_url="http://127.0.0.1:8200")

    with patch.object(client, "encrypt", new_callable=AsyncMock) as mock_enc, \
         patch.object(client, "decrypt", new_callable=AsyncMock) as mock_dec:

        mock_enc.return_value = "vault:v1:89asdf789asdf789asdf"
        mock_dec.return_value = "raw_secret_data"

        ciphertext = await client.encrypt("raw_secret_data")
        assert ciphertext == "vault:v1:89asdf789asdf789asdf"

        plaintext = await client.decrypt(ciphertext)
        assert plaintext == "raw_secret_data"


@pytest.mark.asyncio
async def test_secrets_api_endpoints(async_client: AsyncClient, db_session):
    """Test REST API /api/v1/secrets/status, /encrypt, /decrypt, and /rotate-key."""
    admin = User(
        username="admin_vault_test",
        email="admin_vault@infra.com",
        hashed_password="hash",
        role=UserRole.ADMIN,
        is_active=True,
    )
    db_session.add(admin)
    await db_session.commit()
    token = create_access_token(subject=str(admin.id), role=admin.role.value)
    headers = {"Authorization": f"Bearer {token}"}

    # 1. GET /api/v1/secrets/status
    resp = await async_client.get("/api/v1/secrets/status", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data
    assert data["provider"] == "HashiCorpVaultSecretProvider"

    # 2. POST /api/v1/secrets/encrypt (with mock client)
    with patch("api.v1.secrets.vault_client.encrypt", new_callable=AsyncMock) as mock_enc, \
         patch("api.v1.secrets.vault_client.decrypt", new_callable=AsyncMock) as mock_dec, \
         patch("api.v1.secrets.vault_client.rotate_key", new_callable=AsyncMock) as mock_rot:

        mock_enc.return_value = "vault:v1:mocked_ciphertext_hash"
        mock_dec.return_value = "my_target_ssh_key"
        mock_rot.return_value = {"status": "success", "key_name": "infra-monitoring-key", "message": "Key rotated successfully"}

        # Encrypt
        enc_resp = await async_client.post(
            "/api/v1/secrets/encrypt",
            json={"plaintext": "my_target_ssh_key"},
            headers=headers,
        )
        assert enc_resp.status_code == 200, enc_resp.text
        assert enc_resp.json()["ciphertext"] == "vault:v1:mocked_ciphertext_hash"

        # Decrypt
        dec_resp = await async_client.post(
            "/api/v1/secrets/decrypt",
            json={"ciphertext": "vault:v1:mocked_ciphertext_hash"},
            headers=headers,
        )
        assert dec_resp.status_code == 200, dec_resp.text
        assert dec_resp.json()["plaintext"] == "my_target_ssh_key"

        # Rotate Key
        rot_resp = await async_client.post(
            "/api/v1/secrets/rotate-key",
            json={"key_name": "infra-monitoring-key"},
            headers=headers,
        )
        assert rot_resp.status_code == 200, rot_resp.text
        assert rot_resp.json()["status"] == "success"
