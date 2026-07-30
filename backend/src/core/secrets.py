import os
from abc import ABC, abstractmethod


class BaseSecretProvider(ABC):
    """Abstract Secret Provider boundary for credentials access."""

    @abstractmethod
    def get_secret(self, secret_ref: str) -> str | None:
        """Resolve a secret reference identifier to its payload."""
        pass


class EnvironmentAndFileSecretProvider(BaseSecretProvider):
    """
    Default MVP secret provider.
    Resolves secrets from:
    1. Docker secrets / mounted files (/run/secrets/<name> or secrets/<name>)
    2. Environment variables matching reference name
    """

    def __init__(self, secrets_dir: str = "/run/secrets"):
        self.secrets_dir = secrets_dir

    def get_secret(self, secret_ref: str) -> str | None:
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


# Default global secret provider instance
secret_provider: BaseSecretProvider = EnvironmentAndFileSecretProvider()
