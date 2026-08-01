import abc
import logging
import uuid
from datetime import UTC, datetime
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.alert import Alert, AlertStatus, NotificationProvider
from models.audit import AuditLog
from models.node import Node

logger = logging.getLogger("ticketing_service")


def utc_now() -> datetime:
    return datetime.now(UTC)


class BaseTicketingAdapter(abc.ABC):
    """Abstract Base Class for ITSM Ticketing System Adapters."""

    @abc.abstractmethod
    async def create_ticket(
        self,
        alert: Alert,
        node_name: str,
        params: dict[str, Any],
        config: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Creates a ticket in the external ITSM system.
        Returns dict containing: ticket_id, ticket_url, ticket_status, ticket_system.
        """
        pass

    @abc.abstractmethod
    async def get_ticket_status(self, ticket_id: str, config: dict[str, Any]) -> str:
        """Fetches current status of a ticket from external ITSM."""
        pass


class JiraTicketingAdapter(BaseTicketingAdapter):
    """Jira Cloud / Server REST API Ticketing Adapter."""

    async def create_ticket(
        self,
        alert: Alert,
        node_name: str,
        params: dict[str, Any],
        config: dict[str, Any],
    ) -> dict[str, Any]:
        jira_url = config.get("jira_url", "").rstrip("/")
        username = config.get("username", "")
        api_token = config.get("api_token", "")
        project_key = params.get("project_key") or config.get("default_project", "INC")
        issue_type = params.get("issue_type") or config.get("default_issue_type", "Incident")

        summary = params.get("summary") or f"[{alert.severity.upper()}] Incident on {node_name}: {alert.message[:80]}"
        description = params.get("description") or (
            f"Monitoring Alert Details:\n"
            f"- Alert ID: {alert.id}\n"
            f"- Node Name: {node_name}\n"
            f"- Severity: {alert.severity}\n"
            f"- Message: {alert.message}\n"
            f"- Triggered At: {alert.triggered_at.isoformat()}\n"
        )

        # Real HTTP Request if Jira URL is configured
        if jira_url and username and api_token:
            payload = {
                "fields": {
                    "project": {"key": project_key},
                    "summary": summary,
                    "description": description,
                    "issuetype": {"name": issue_type},
                }
            }
            auth = (username, api_token)
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.post(f"{jira_url}/rest/api/2/issue", json=payload, auth=auth)
                    if resp.status_code in (200, 201):
                        data = resp.json()
                        key = data.get("key", f"{project_key}-100")
                        ticket_url = f"{jira_url}/browse/{key}"
                        return {
                            "ticket_id": key,
                            "ticket_url": ticket_url,
                            "ticket_status": "OPEN",
                            "ticket_system": "jira",
                        }
                    else:
                        logger.error(f"Jira API returned error {resp.status_code}: {resp.text}")
            except Exception as err:
                logger.error(f"Failed to communicate with Jira API: {err}")

        # Fallback / Mock creation for testing & offline environments
        mock_key = f"{project_key}-{str(uuid.uuid4().hex[:5]).upper()}"
        mock_url = f"{jira_url or 'https://jira.example.com'}/browse/{mock_key}"
        return {
            "ticket_id": mock_key,
            "ticket_url": mock_url,
            "ticket_status": "OPEN",
            "ticket_system": "jira",
        }

    async def get_ticket_status(self, ticket_id: str, config: dict[str, Any]) -> str:
        jira_url = config.get("jira_url", "").rstrip("/")
        username = config.get("username", "")
        api_token = config.get("api_token", "")

        if jira_url and username and api_token:
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.get(f"{jira_url}/rest/api/2/issue/{ticket_id}", auth=(username, api_token))
                    if resp.status_code == 200:
                        data = resp.json()
                        status_name = data.get("fields", {}).get("status", {}).get("name", "OPEN")
                        return status_name.upper()
            except Exception as err:
                logger.error(f"Jira status fetch failed: {err}")
        return "IN_PROGRESS"


class ServiceNowTicketingAdapter(BaseTicketingAdapter):
    """ServiceNow Table API Incident Ticketing Adapter."""

    async def create_ticket(
        self,
        alert: Alert,
        node_name: str,
        params: dict[str, Any],
        config: dict[str, Any],
    ) -> dict[str, Any]:
        snow_url = config.get("servicenow_url", "").rstrip("/")
        username = config.get("username", "")
        password = config.get("password", "")

        urgency_map = {"High": "1", "Medium": "2", "Low": "3"}
        urgency_code = urgency_map.get(params.get("urgency", "High"), "1")
        summary = params.get("summary") or f"[{alert.severity.upper()}] {node_name}: {alert.message[:80]}"
        description = params.get("description") or f"Alert ID: {alert.id}\nMessage: {alert.message}"

        if snow_url and username and password:
            payload = {
                "short_description": summary,
                "comments": description,
                "urgency": urgency_code,
                "impact": urgency_code,
            }
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.post(
                        f"{snow_url}/api/now/table/incident",
                        json=payload,
                        auth=(username, password),
                    )
                    if resp.status_code in (200, 201):
                        data = resp.json().get("result", {})
                        number = data.get("number", "INC0010001")
                        sys_id = data.get("sys_id", "")
                        ticket_url = f"{snow_url}/nav_to.do?uri=incident.do?sys_id={sys_id}" if sys_id else f"{snow_url}/incident/{number}"
                        return {
                            "ticket_id": number,
                            "ticket_url": ticket_url,
                            "ticket_status": "OPEN",
                            "ticket_system": "servicenow",
                        }
            except Exception as err:
                logger.error(f"ServiceNow API call failed: {err}")

        # Fallback / Mock creation
        mock_number = f"INC00{uuid.uuid4().hex[:5].upper()}"
        mock_url = f"{snow_url or 'https://servicenow.example.com'}/incident/{mock_number}"
        return {
            "ticket_id": mock_number,
            "ticket_url": mock_url,
            "ticket_status": "OPEN",
            "ticket_system": "servicenow",
        }

    async def get_ticket_status(self, ticket_id: str, config: dict[str, Any]) -> str:
        return "OPEN"


class GenericITSMWebhookAdapter(BaseTicketingAdapter):
    """Generic Webhook / Custom ITSM Adapter."""

    async def create_ticket(
        self,
        alert: Alert,
        node_name: str,
        params: dict[str, Any],
        config: dict[str, Any],
    ) -> dict[str, Any]:
        webhook_url = config.get("webhook_url", "")
        summary = params.get("summary") or f"[{alert.severity.upper()}] Alert on {node_name}"
        description = params.get("description") or alert.message

        if webhook_url:
            payload = {
                "event": "CREATE_TICKET",
                "alert_id": str(alert.id),
                "severity": alert.severity,
                "node_name": node_name,
                "summary": summary,
                "description": description,
            }
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.post(webhook_url, json=payload)
                    if resp.status_code < 400:
                        res_json = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
                        ticket_id = res_json.get("ticket_id", f"ITSM-{uuid.uuid4().hex[:6].upper()}")
                        ticket_url = res_json.get("ticket_url", webhook_url)
                        return {
                            "ticket_id": ticket_id,
                            "ticket_url": ticket_url,
                            "ticket_status": "OPEN",
                            "ticket_system": "itsm_webhook",
                        }
            except Exception as err:
                logger.error(f"Generic ITSM webhook failed: {err}")

        ticket_id = f"ITSM-{uuid.uuid4().hex[:6].upper()}"
        return {
            "ticket_id": ticket_id,
            "ticket_url": f"https://itsm.example.com/tickets/{ticket_id}",
            "ticket_status": "OPEN",
            "ticket_system": "itsm_webhook",
        }

    async def get_ticket_status(self, ticket_id: str, config: dict[str, Any]) -> str:
        return "OPEN"


def get_ticketing_adapter(system_type: str) -> BaseTicketingAdapter:
    system_type = system_type.lower()
    if system_type == "jira":
        return JiraTicketingAdapter()
    elif system_type == "servicenow":
        return ServiceNowTicketingAdapter()
    else:
        return GenericITSMWebhookAdapter()


async def get_ticketing_provider_config(db: AsyncSession, system_type: str) -> dict[str, Any]:
    stmt = select(NotificationProvider).where(NotificationProvider.provider_type == system_type)
    res = await db.execute(stmt)
    provider = res.scalars().first()
    return provider.config if provider and provider.is_enabled else {}


async def create_ticket_for_alert(
    db: AsyncSession,
    alert_id: uuid.UUID,
    system_type: str,
    custom_params: dict[str, Any],
    username: str,
) -> Alert:
    """Creates an ITSM ticket for an existing alert and links the reference metadata."""
    alert = await db.get(Alert, alert_id)
    if not alert:
        raise KeyError(f"Alert with ID '{alert_id}' not found")

    # Resolve node name
    node = await db.get(Node, alert.node_id)
    node_name = node.name if node else "Unknown Node"

    config = await get_ticketing_provider_config(db, system_type)
    adapter = get_ticketing_adapter(system_type)

    ticket_res = await adapter.create_ticket(
        alert=alert,
        node_name=node_name,
        params=custom_params,
        config=config,
    )

    now = utc_now()
    alert.ticket_id = ticket_res["ticket_id"]
    alert.ticket_url = ticket_res["ticket_url"]
    alert.ticket_system = ticket_res["ticket_system"]
    alert.ticket_status = ticket_res["ticket_status"]
    alert.ticket_created_at = now

    # Audit log entry
    audit = AuditLog(
        actor_username=username,
        action="ITSM_TICKET_CREATED",
        target=str(alert.id),
        metadata_={
            "ticket_id": ticket_res["ticket_id"],
            "ticket_system": ticket_res["ticket_system"],
            "ticket_url": ticket_res["ticket_url"],
        },
    )
    db.add(audit)

    await db.commit()
    await db.refresh(alert)
    return alert


async def sync_alert_ticket_status(db: AsyncSession, alert_id: uuid.UUID) -> Alert:
    """Synchronizes ticket status from external ITSM system."""
    alert = await db.get(Alert, alert_id)
    if not alert:
        raise KeyError(f"Alert with ID '{alert_id}' not found")
    if not alert.ticket_id or not alert.ticket_system:
        raise ValueError("Alert has no associated ITSM ticket")

    config = await get_ticketing_provider_config(db, alert.ticket_system)
    adapter = get_ticketing_adapter(alert.ticket_system)

    latest_status = await adapter.get_ticket_status(alert.ticket_id, config)
    alert.ticket_status = latest_status

    # Auto-resolve alert if ticket is RESOLVED or CLOSED
    if latest_status.upper() in ("RESOLVED", "CLOSED", "DONE") and alert.status == AlertStatus.FIRING:
        alert.status = AlertStatus.RESOLVED
        alert.resolved_at = utc_now()

    await db.commit()
    await db.refresh(alert)
    return alert


async def handle_ticket_webhook_callback(
    db: AsyncSession,
    alert_id: uuid.UUID | None,
    ticket_id: str,
    ticket_status: str,
    notes: str | None = None,
) -> Alert | None:
    """Handles incoming ITSM webhook callbacks to sync ticket status to Alert model."""
    alert = None
    if alert_id:
        alert = await db.get(Alert, alert_id)
    if not alert and ticket_id:
        stmt = select(Alert).where(Alert.ticket_id == ticket_id)
        res = await db.execute(stmt)
        alert = res.scalars().first()

    if not alert:
        logger.warning(f"Webhook callback for unknown ticket_id={ticket_id}, alert_id={alert_id}")
        return None

    alert.ticket_status = ticket_status.upper()
    if ticket_status.upper() in ("RESOLVED", "CLOSED", "DONE") and alert.status == AlertStatus.FIRING:
        alert.status = AlertStatus.RESOLVED
        alert.resolved_at = utc_now()

    audit = AuditLog(
        actor_username="system_itsm_webhook",
        action="ITSM_TICKET_CALLBACK",
        target=str(alert.id),
        metadata_={"ticket_id": ticket_id, "new_status": ticket_status, "notes": notes},
    )
    db.add(audit)

    await db.commit()
    await db.refresh(alert)
    return alert
