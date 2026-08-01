import logging
import os
from abc import ABC, abstractmethod
from typing import Optional

from core.vault_client import HashiCorpVaultClient

logger = logging.getLogger("secret_provider")


class BaseSecretProvider(ABC):
    """Abstract Secret Provider boundary for credentials access."""

    @abstractmethod
    def get_secret(self, secret_ref: str) -> Optional[str]:
        """Resolve a secret reference identifier to its payload."""
        pass


class EnvironmentAndFileSecretProvider(BaseSecretProvider):
    """
    Default fallback secret provider.
    Resolves secrets from:
    1. Docker secrets / mounted files (/run/secrets/<name> or secrets/<name>)
    2. Environment variables matching reference name
    """

    def __init__(self, secrets_dir: str = "/run/secrets"):
        self.secrets_dir = secrets_dir

    def get_secret(self, secret_ref: str) -> Optional[str]:
        if not secret_ref:
            return None

        # Clean reference prefix if present (e.g. "secret:my_key" -> "my_key")
        clean_ref = secret_ref.split(":")[-1]

        # 1. Check Docker secrets mounted file
        file_path = os.path.join(self.secrets_dir, clean_ref)
        if os.path.exists(file_path) and os.path.isfile(file_path):
            try:
                with open(file_path, encoding="utf-8") as f:
                    return f.read().strip()
            except Exception:
                pass

        # 2. Check local secrets dir fallback (e.g., ./secrets/<clean_ref>)
        local_path = os.path.join("secrets", clean_ref)
        if os.path.exists(local_path) and os.path.isfile(local_path):
            try:
                with open(local_path, encoding="utf-8") as f:
                    return f.read().strip()
            except Exception:
                pass

        # 3. Check environment variable
        env_val = os.getenv(clean_ref) or os.getenv(clean_ref.upper())
        if env_val:
            return env_val

        return None


class HashiCorpVaultSecretProvider(BaseSecretProvider):
    """
    External Secrets Provider integrating HashiCorp Vault.
    Provides seamless automatic fallback to EnvironmentAndFileSecretProvider.
    """

    def __init__(self, vault_client: Optional[HashiCorpVaultClient] = None):
        self.client = vault_client or HashiCorpVaultClient()
        self.fallback_provider = EnvironmentAndFileSecretProvider()

    def get_secret(self, secret_ref: str) -> Optional[str]:
        if not secret_ref:
            return None

        # 1. If reference is a Vault Transit Ciphertext (starts with "vault:v1:"), attempt inline decryption
        if secret_ref.startswith("vault:v1:"):
            try:
                import asyncio
                # Run sync in loop if available or fallback
                loop = None
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    pass

                if loop and loop.is_running():
                    # In async context, execute fallback or sync call
                    pass
                else:
                    decrypted = asyncio.run(self.client.decrypt(secret_ref))
                    if decrypted:
                        return decrypted
            except Exception as err:
                logger.warning(f"Vault Transit decryption failed for reference '{secret_ref}': {err}")

        # 2. Check fallback provider (Environment & File secrets)
        fallback_val = self.fallback_provider.get_secret(secret_ref)
        if fallback_val:
            return fallback_val

        return None


# Global secret provider initialization based on environment config
def get_global_secret_provider() -> BaseSecretProvider:
    vault_enabled = os.getenv("VAULT_ENABLED", "true").lower() in ("true", "1", "yes")
    if vault_enabled:
        return HashiCorpVaultSecretProvider()
    return EnvironmentAndFileSecretProvider()


secret_provider: BaseSecretProvider = get_global_secret_provider()
