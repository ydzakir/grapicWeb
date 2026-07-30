from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from models.audit import AuditLog

# Keys to automatically redact from audit log metadata
SENSITIVE_KEYS = {
    "password", "hashed_password", "token", "access_token",
    "secret", "secret_key", "private_key", "authorization",
    "cookie", "session", "credential"
}


def sanitize_metadata(data: dict[str, Any]) -> dict[str, Any]:
    """Recursively sanitize metadata dictionary to remove any sensitive secrets or tokens."""
    if not isinstance(data, dict):
        return data

    sanitized = {}
    for key, value in data.items():
        if any(sensitive in key.lower() for sensitive in SENSITIVE_KEYS):
            sanitized[key] = "[REDACTED]"
        elif isinstance(value, dict):
            sanitized[key] = sanitize_metadata(value)
        elif isinstance(value, list):
            sanitized[key] = [
                sanitize_metadata(item) if isinstance(item, dict) else item
                for item in value
            ]
        else:
            sanitized[key] = value
    return sanitized


async def log_audit_event(
    db: AsyncSession,
    actor_username: str,
    action: str,
    target: str | None = None,
    ip_address: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> AuditLog:
    """Record an audit log entry in the database with automatic secret redaction."""
    clean_metadata = sanitize_metadata(metadata or {})

    audit_entry = AuditLog(
        actor_username=actor_username or "anonymous",
        action=action,
        target=target,
        ip_address=ip_address,
        metadata_=clean_metadata,
    )
    db.add(audit_entry)
    await db.flush()
    return audit_entry
