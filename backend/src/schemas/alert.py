import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AlertRuleCreate(BaseModel):
    node_id: uuid.UUID | None = None
    group_name: str | None = None
    metric_name: str
    warning_threshold: float | None = None
    critical_threshold: float | None = None
    duration_seconds: int = 300
    is_enabled: bool = True


class AlertRuleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    node_id: uuid.UUID | None = None
    group_name: str | None = None
    metric_name: str
    warning_threshold: float | None = None
    critical_threshold: float | None = None
    duration_seconds: int
    is_enabled: bool
    created_at: datetime


class AlertResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    node_id: uuid.UUID
    rule_id: uuid.UUID | None = None
    severity: str
    status: str
    message: str
    triggered_at: datetime
    resolved_at: datetime | None = None
    acknowledged_at: datetime | None = None
    acknowledged_by: str | None = None
    escalated: bool
    ticket_id: str | None = None
    ticket_url: str | None = None
    ticket_system: str | None = None
    ticket_status: str | None = None
    ticket_created_at: datetime | None = None


class AlertAcknowledgeRequest(BaseModel):
    note: str | None = "Acknowledged by operator"


class CreateTicketRequest(BaseModel):
    system_type: str = "jira" # jira, servicenow, or itsm_webhook
    project_key: str | None = "INC" # Jira Project Key or ServiceNow Category
    issue_type: str | None = "Incident" # Jira Issue Type or ServiceNow Category
    urgency: str | None = "High" # High, Medium, Low
    summary: str | None = None
    description: str | None = None


class TicketSyncResponse(BaseModel):
    alert_id: uuid.UUID
    ticket_id: str
    ticket_system: str
    ticket_status: str
    ticket_url: str | None = None
    synced_at: datetime


class TicketingWebhookCallback(BaseModel):
    alert_id: uuid.UUID | None = None
    ticket_id: str
    ticket_status: str
    notes: str | None = None

