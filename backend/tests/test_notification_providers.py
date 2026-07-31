import pytest
import respx
from httpx import Response
from services.notification_service import (
    LogNotificationProvider,
    WebhookNotificationProvider,
    EmailNotificationProvider,
    get_notification_provider,
)


@pytest.mark.asyncio
async def test_log_notification_provider():
    provider = LogNotificationProvider()
    success = await provider.send_notification(
        title="Test Alert",
        message="CPU high warning",
        severity="warning",
        details={"value": 87.5},
    )
    assert success is True


@pytest.mark.asyncio
async def test_webhook_notification_provider_success():
    webhook_url = "https://hooks.slack.example.com/services/test"
    provider = WebhookNotificationProvider(config={"webhook_url": webhook_url})

    with respx.mock:
        respx.post(webhook_url).mock(return_value=Response(200, json={"status": "ok"}))
        success = await provider.send_notification(
            title="Critical Alert",
            message="Server Down Critical",
            severity="critical",
            details={"node_id": "test-123"},
        )
        assert success is True


def test_get_notification_provider_factory():
    log_p = get_notification_provider("log")
    assert isinstance(log_p, LogNotificationProvider)

    web_p = get_notification_provider("webhook", {"webhook_url": "http://test"})
    assert isinstance(web_p, WebhookNotificationProvider)

    email_p = get_notification_provider("email", {"to_email": "ops@infra.com"})
    assert isinstance(email_p, EmailNotificationProvider)
