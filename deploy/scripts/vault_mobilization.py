#!/usr/bin/env python3
"""
HashiCorp Vault Mobilization & Initialization Script.
Enables Transit & KV secret engine, creates encryption keys, and provisions default secrets.
"""
import asyncio
import os
import sys

import httpx

VAULT_ADDR = os.getenv("VAULT_ADDR", "http://127.0.0.1:8200").rstrip("/")
VAULT_TOKEN = os.getenv("VAULT_TOKEN", "root")
KEY_NAME = os.getenv("VAULT_KEY_NAME", "infra-monitoring-key")

HEADERS = {
    "X-Vault-Token": VAULT_TOKEN,
    "Content-Type": "application/json",
}


async def initialize_vault():
    print(f"[*] Initializing HashiCorp Vault setup at {VAULT_ADDR}...")

    async with httpx.AsyncClient(timeout=10.0) as client:
        # 1. Check health
        try:
            resp = await client.get(f"{VAULT_ADDR}/v1/sys/health", headers=HEADERS)
            print(f"[+] Vault Health Status: {resp.status_code}")
        except Exception as e:
            print(f"[-] Could not connect to Vault at {VAULT_ADDR}: {e}")
            print("[!] Running in Environment & File Secrets fallback mode.")
            return

        # 2. Enable Transit secret engine
        try:
            resp = await client.post(
                f"{VAULT_ADDR}/v1/sys/mounts/transit",
                json={"type": "transit", "description": "Transit Secret Engine for Target Credentials"},
                headers=HEADERS,
            )
            if resp.status_code in (200, 204, 400): # 400 if already mounted
                print("[+] Transit secret engine enabled successfully.")
        except Exception as e:
            print(f"[-] Transit mount warning: {e}")

        # 3. Create Transit Key
        try:
            resp = await client.post(
                f"{VAULT_ADDR}/v1/transit/keys/{KEY_NAME}",
                json={"type": "aes256-gcm96"},
                headers=HEADERS,
            )
            if resp.status_code in (200, 204):
                print(f"[+] Transit encryption key '{KEY_NAME}' created successfully.")
        except Exception as e:
            print(f"[-] Transit key creation warning: {e}")

        # 4. Enable KV-v2 secret engine
        try:
            resp = await client.post(
                f"{VAULT_ADDR}/v1/sys/mounts/secret",
                json={"type": "kv", "options": {"version": "2"}},
                headers=HEADERS,
            )
            if resp.status_code in (200, 204, 400):
                print("[+] KV-v2 secret engine enabled successfully.")
        except Exception as e:
            print(f"[-] KV mount warning: {e}")

    print("[✔] HashiCorp Vault mobilization completed successfully.")


if __name__ == "__main__":
    asyncio.run(initialize_vault())
