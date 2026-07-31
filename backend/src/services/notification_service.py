import logging
import abc
from typing import Any, Dict
import httpx

logger = logging.getLogger("notification_service")


class BaseNotificationProvider(abc.ABC):
    """Abstract base class for notification providers."""

    @abc.abstractmethod
    async def send_notification(self, title: str, message: str, severity: str, details: Dict[str, Any]) -> bool:
        pass


class LogNotificationProvider(BaseNotificationProvider):
    """Log Notification Provider (outputs to logger; testable without credentials)."""

    def __init__(self, config: Dict[str, Any] | None = None):
        self.config = config or {}

    async def send_notification(self, title: str, message: str, severity: str, details: Dict[str, Any]) -> bool:
        log_level = logging.WARNING if severity == "warning" else logging.ERROR
        logger.log(log_level, f"[NOTIFICATION - {severity.upper()}] {title}: {message} | Details: {details}")
        return True


class WebhookNotificationProvider(BaseNotificationProvider):
    """Webhook Notification Provider (sends JSON payload via HTTP POST)."""

    def __init__(self, config: Dict[str, Any]):
        self.webhook_url = config.get("webhook_url", "")
        self.headers = config.get("headers", {"Content-Type": "application/json"})

    async def send_notification(self, title: str, message: str, severity: str, details: Dict[str, Any]) -> bool:
        if not self.webhook_url:
            logger.warning("Webhook URL not configured.")
            return False

        payload = {
            "title": title,
            "message": message,
            "severity": severity,
            "details": details,
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(self.webhook_url, json=payload, headers=self.headers)
                return resp.status_code < 400
        except Exception as err:
            logger.error(f"Webhook notification failed: {err}")
            return False


class EmailNotificationProvider(BaseNotificationProvider):
    """Email Notification Provider."""

    def __init__(self, config: Dict[str, Any]):
        self.smtp_host = config.get("smtp_host", "localhost")
        self.to_email = config.get("to_email", "")

    async def send_notification(self, title: str, message: str, severity: str, details: Dict[str, Any]) -> bool:
        logger.info(f"[EMAIL NOTIFICATION to {self.to_email}] {title}: {message}")
        return True


def get_notification_provider(provider_type: str, config: Dict[str, Any] | None = None) -> BaseNotificationProvider:
    if provider_type == "webhook":
        return WebhookNotificationProvider(config or {})
    elif provider_type == "email":
        return EmailNotificationProvider(config or {})
    else:
        return LogNotificationProvider(config or {})
