from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_user, require_role
from core.database import get_db
from core.vault_client import HashiCorpVaultClient
from models.audit import AuditLog
from models.user import User, UserRole
from schemas.secret import (
    KeyRotationRequest,
    KeyRotationResponse,
    SecretDecryptRequest,
    SecretDecryptResponse,
    SecretEncryptRequest,
    SecretEncryptResponse,
    VaultStatusResponse,
)

require_admin_role = require_role([UserRole.ADMIN])

router = APIRouter(prefix="/secrets", tags=["External Secrets & Vault"])

vault_client = HashiCorpVaultClient()


@router.get("/status", response_model=VaultStatusResponse)
async def get_vault_status(
    current_user: User = Depends(get_current_user),
):
    """Retrieve health and connectivity status of HashiCorp Vault server."""
    health_info = await vault_client.check_health()
    return VaultStatusResponse(**health_info)


@router.post("/encrypt", response_model=SecretEncryptResponse)
async def encrypt_secret_endpoint(
    body: SecretEncryptRequest,
    current_user: User = Depends(get_current_user),
):
    """Encrypt raw secret credential using HashiCorp Vault Transit engine."""
    ciphertext = await vault_client.encrypt(plaintext=body.plaintext, key_name=body.key_name)
    if not ciphertext:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Vault Transit encryption failed. Verify Vault server connection and transit key configuration.",
        )
    return SecretEncryptResponse(
        ciphertext=ciphertext,
        key_name=body.key_name or vault_client.key_name,
        system="hashicorp_vault_transit",
    )


@router.post("/decrypt", response_model=SecretDecryptResponse)
async def decrypt_secret_endpoint(
    body: SecretDecryptRequest,
    current_user: User = Depends(require_admin_role),
):
    """Decrypt Vault Transit ciphertext back to raw plaintext (Admin only)."""
    plaintext = await vault_client.decrypt(ciphertext=body.ciphertext, key_name=body.key_name)
    if plaintext is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Vault Transit decryption failed. Invalid ciphertext or key version mismatch.",
        )
    return SecretDecryptResponse(
        plaintext=plaintext,
        key_name=body.key_name or vault_client.key_name,
    )


@router.post("/rotate-key", response_model=KeyRotationResponse)
async def rotate_vault_key_endpoint(
    body: KeyRotationRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin_role),
):
    """Trigger rotation of the underlying Transit key version in HashiCorp Vault (Admin only)."""
    res = await vault_client.rotate_key(key_name=body.key_name)
    if res.get("status") != "success":
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=res.get("message", "Key rotation failed"),
        )

    # Log audit entry
    audit = AuditLog(
        actor_username=current_user.username,
        action="VAULT_KEY_ROTATED",
        target=body.key_name or vault_client.key_name,
        metadata_={"result": res},
    )
    db.add(audit)
    await db.commit()

    return KeyRotationResponse(
        status="success",
        key_name=body.key_name or vault_client.key_name,
        message="HashiCorp Vault Transit encryption key version rotated successfully.",
    )
