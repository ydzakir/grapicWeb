import base64
import logging
import os
from typing import Any, Dict, Optional
import httpx

logger = logging.getLogger("vault_client")


class HashiCorpVaultClient:
    """
    Client wrapper for HashiCorp Vault Transit Engine and KV Secret Engine.
    Uses HTTP REST API calls via httpx.
    """

    def __init__(
        self,
        vault_url: Optional[str] = None,
        token: Optional[str] = None,
        key_name: str = "infra-monitoring-key",
        namespace: Optional[str] = None,
        timeout: float = 5.0,
    ):
        self.vault_url = (vault_url or os.getenv("VAULT_ADDR", "http://127.0.0.1:8200")).rstrip("/")
        self.token = token or os.getenv("VAULT_TOKEN", "root")
        self.key_name = key_name or os.getenv("VAULT_KEY_NAME", "infra-monitoring-key")
        self.namespace = namespace or os.getenv("VAULT_NAMESPACE")
        self.timeout = timeout

    def _get_headers(self) -> Dict[str, str]:
        headers = {
            "X-Vault-Token": self.token,
            "Content-Type": "application/json",
        }
        if self.namespace:
            headers["X-Vault-Namespace"] = self.namespace
        return headers

    async def check_health(self) -> Dict[str, Any]:
        """Checks HashiCorp Vault server health and seal status."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(f"{self.vault_url}/v1/sys/health", headers=self._get_headers())
                if resp.status_code in (200, 429, 501, 503):
                    data = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
                    return {
                        "status": "connected",
                        "initialized": data.get("initialized", True),
                        "sealed": data.get("sealed", False),
                        "version": data.get("version", "unknown"),
                        "vault_url": self.vault_url,
                    }
        except Exception as err:
            logger.warning(f"Vault health check failed: {err}")

        return {
            "status": "disconnected",
            "initialized": False,
            "sealed": True,
            "version": None,
            "vault_url": self.vault_url,
        }

    async def encrypt(self, plaintext: str, key_name: Optional[str] = None) -> Optional[str]:
        """Encrypts plaintext string using Vault Transit engine."""
        target_key = key_name or self.key_name
        encoded_payload = base64.b64encode(plaintext.encode("utf-8")).decode("utf-8")
        url = f"{self.vault_url}/v1/transit/encrypt/{target_key}"
        payload = {"plaintext": encoded_payload}

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(url, json=payload, headers=self._get_headers())
                if resp.status_code == 200:
                    data = resp.json()
                    return data.get("data", {}).get("ciphertext")
                else:
                    logger.error(f"Vault encrypt error {resp.status_code}: {resp.text}")
        except Exception as err:
            logger.error(f"Vault Transit encrypt call failed: {err}")

        return None

    async def decrypt(self, ciphertext: str, key_name: Optional[str] = None) -> Optional[str]:
        """Decrypts Vault Transit ciphertext string back to plaintext."""
        target_key = key_name or self.key_name
        url = f"{self.vault_url}/v1/transit/decrypt/{target_key}"
        payload = {"ciphertext": ciphertext}

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(url, json=payload, headers=self._get_headers())
                if resp.status_code == 200:
                    data = resp.json()
                    b64_plaintext = data.get("data", {}).get("plaintext", "")
                    return base64.b64decode(b64_plaintext.encode("utf-8")).decode("utf-8")
                else:
                    logger.error(f"Vault decrypt error {resp.status_code}: {resp.text}")
        except Exception as err:
            logger.error(f"Vault Transit decrypt call failed: {err}")

        return None

    async def rotate_key(self, key_name: Optional[str] = None) -> Dict[str, Any]:
        """Rotates the underlying key version for Vault Transit engine."""
        target_key = key_name or self.key_name
        url = f"{self.vault_url}/v1/transit/keys/{target_key}/rotate"

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(url, json={}, headers=self._get_headers())
                if resp.status_code in (200, 204):
                    return {"status": "success", "key_name": target_key, "message": "Key rotated successfully"}
                else:
                    logger.error(f"Vault key rotate error {resp.status_code}: {resp.text}")
        except Exception as err:
            logger.error(f"Vault key rotation failed: {err}")

        return {"status": "error", "key_name": target_key, "message": "Rotation call failed"}

    async def rewrap(self, ciphertext: str, key_name: Optional[str] = None) -> Optional[str]:
        """Rewraps ciphertext using the latest version of Transit encryption key."""
        target_key = key_name or self.key_name
        url = f"{self.vault_url}/v1/transit/rewrap/{target_key}"
        payload = {"ciphertext": ciphertext}

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(url, json=payload, headers=self._get_headers())
                if resp.status_code == 200:
                    data = resp.json()
                    return data.get("data", {}).get("ciphertext")
        except Exception as err:
            logger.error(f"Vault rewrap call failed: {err}")

        return None

    async def get_kv_secret(self, path: str) -> Optional[Dict[str, Any]]:
        """Fetches secret data payload from Vault KV Engine v2 (/v1/secret/data/{path})."""
        clean_path = path.lstrip("/")
        url = f"{self.vault_url}/v1/secret/data/{clean_path}"

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(url, headers=self._get_headers())
                if resp.status_code == 200:
                    data = resp.json()
                    return data.get("data", {}).get("data")
        except Exception as err:
            logger.warning(f"Vault KV secret fetch failed: {err}")

        return None
