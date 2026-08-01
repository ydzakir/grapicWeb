import abc
import logging
from typing import Any

import httpx

logger = logging.getLogger("notification_service")


class BaseNotificationProvider(abc.ABC):
    """Abstract base class for notification providers."""

    @abc.abstractmethod
    async def send_notification(
        self,
        title: str,
        message: str,
        severity: str,
        details: dict[str, Any],
        attachments: list[str] | None = None,
        html_body: str | None = None,
    ) -> bool:
        pass


class LogNotificationProvider(BaseNotificationProvider):
    """Log Notification Provider (outputs to logger; testable without credentials)."""

    def __init__(self, config: dict[str, Any] | None = None):
        self.config = config or {}

    async def send_notification(
        self,
        title: str,
        message: str,
        severity: str,
        details: dict[str, Any],
        attachments: list[str] | None = None,
        html_body: str | None = None,
    ) -> bool:
        log_level = logging.WARNING if severity == "warning" else logging.ERROR
        logger.log(log_level, f"[NOTIFICATION - {severity.upper()}] {title}: {message} | Details: {details} | Attachments: {attachments}")
        return True


class WebhookNotificationProvider(BaseNotificationProvider):
    """Webhook Notification Provider (sends JSON payload via HTTP POST)."""

    def __init__(self, config: dict[str, Any]):
        self.webhook_url = config.get("webhook_url", "")
        self.headers = config.get("headers", {"Content-Type": "application/json"})

    async def send_notification(
        self,
        title: str,
        message: str,
        severity: str,
        details: dict[str, Any],
        attachments: list[str] | None = None,
        html_body: str | None = None,
    ) -> bool:
        if not self.webhook_url:
            logger.warning("Webhook URL not configured.")
            return False

        payload = {
            "title": title,
            "message": message,
            "severity": severity,
            "details": details,
            "attachments": attachments or [],
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(self.webhook_url, json=payload, headers=self.headers)
                return resp.status_code < 400
        except Exception as err:
            logger.error(f"Webhook notification failed: {err}")
            return False


import asyncio
import os
import smtplib
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def _send_smtp_sync(
    smtp_host: str,
    smtp_port: int,
    smtp_user: str,
    smtp_pass: str,
    smtp_from: str,
    to_email: str,
    title: str,
    message: str,
    html_body: str | None = None,
    attachments: list[str] | None = None,
) -> bool:
    try:
        msg = MIMEMultipart("mixed" if attachments else "alternative")
        msg["Subject"] = title
        msg["From"] = smtp_from
        msg["To"] = to_email

        msg.attach(MIMEText(message, "plain", "utf-8"))
        if html_body:
            msg.attach(MIMEText(html_body, "html", "utf-8"))

        if attachments:
            for filepath in attachments:
                if os.path.exists(filepath):
                    filename = os.path.basename(filepath)
                    with open(filepath, "rb") as f:
                        part = MIMEApplication(f.read(), Name=filename)
                    part["Content-Disposition"] = f'attachment; filename="{filename}"'
                    msg.attach(part)

        server = smtplib.SMTP(smtp_host, smtp_port, timeout=10)
        if smtp_user and smtp_pass:
            server.starttls()
            server.login(smtp_user, smtp_pass)
        server.sendmail(smtp_from, [to_email], msg.as_string())
        server.quit()
        logger.info(f"Email notification successfully sent to {to_email} via {smtp_host}:{smtp_port}")
        return True
    except Exception as exc:
        logger.warning(f"SMTP email notification to {to_email} failed (logged as fallback): {exc}")
        return False


class EmailNotificationProvider(BaseNotificationProvider):
    """Email Notification Provider using SMTP."""

    def __init__(self, config: dict[str, Any]):
        self.smtp_host = config.get("smtp_host", "localhost")
        self.smtp_port = int(config.get("smtp_port", 25))
        self.smtp_user = config.get("smtp_user", "")
        self.smtp_pass = config.get("smtp_pass", "")
        self.smtp_from = config.get("smtp_from", "noreply@monitoring.infra")
        self.to_email = config.get("to_email", "")

    async def send_notification(
        self,
        title: str,
        message: str,
        severity: str,
        details: dict[str, Any],
        attachments: list[str] | None = None,
        html_body: str | None = None,
    ) -> bool:
        to_addr = details.get("recipient") or self.to_email
        if not to_addr:
            logger.warning("No target recipient email configured.")
            return False

        return await asyncio.to_thread(
            _send_smtp_sync,
            smtp_host=self.smtp_host,
            smtp_port=self.smtp_port,
            smtp_user=self.smtp_user,
            smtp_pass=self.smtp_pass,
            smtp_from=self.smtp_from,
            to_email=to_addr,
            title=title,
            message=message,
            html_body=html_body,
            attachments=attachments,
        )


def get_notification_provider(provider_type: str, config: dict[str, Any] | None = None) -> BaseNotificationProvider:
    if provider_type == "webhook":
        return WebhookNotificationProvider(config or {})
    elif provider_type == "email":
        return EmailNotificationProvider(config or {})
    else:
        return LogNotificationProvider(config or {})
