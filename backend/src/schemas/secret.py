from pydantic import BaseModel, Field


class SecretEncryptRequest(BaseModel):
    plaintext: str = Field(..., min_length=1)
    key_name: str | None = "infra-monitoring-key"


class SecretEncryptResponse(BaseModel):
    ciphertext: str
    key_name: str
    system: str = "hashicorp_vault_transit"


class SecretDecryptRequest(BaseModel):
    ciphertext: str = Field(..., min_length=1)
    key_name: str | None = "infra-monitoring-key"


class SecretDecryptResponse(BaseModel):
    plaintext: str
    key_name: str


class KeyRotationRequest(BaseModel):
    key_name: str | None = "infra-monitoring-key"


class KeyRotationResponse(BaseModel):
    status: str
    key_name: str
    message: str


class VaultStatusResponse(BaseModel):
    status: str # connected / disconnected
    initialized: bool
    sealed: bool
    version: str | None = None
    vault_url: str
    provider: str = "HashiCorpVaultSecretProvider"
