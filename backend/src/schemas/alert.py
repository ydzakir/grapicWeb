import uuid
from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, ConfigDict


class AlertRuleCreate(BaseModel):
    node_id: Optional[uuid.UUID] = None
    group_name: Optional[str] = None
    metric_name: str
    warning_threshold: Optional[float] = None
    critical_threshold: Optional[float] = None
    duration_seconds: int = 300
    is_enabled: bool = True


class AlertRuleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    node_id: Optional[uuid.UUID] = None
    group_name: Optional[str] = None
    metric_name: str
    warning_threshold: Optional[float] = None
    critical_threshold: Optional[float] = None
    duration_seconds: int
    is_enabled: bool
    created_at: datetime


class AlertResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    node_id: uuid.UUID
    rule_id: Optional[uuid.UUID] = None
    severity: str
    status: str
    message: str
    triggered_at: datetime
    resolved_at: Optional[datetime] = None
    acknowledged_at: Optional[datetime] = None
    acknowledged_by: Optional[str] = None
    escalated: bool
    ticket_id: Optional[str] = None
    ticket_url: Optional[str] = None
    ticket_system: Optional[str] = None
    ticket_status: Optional[str] = None
    ticket_created_at: Optional[datetime] = None


class AlertAcknowledgeRequest(BaseModel):
    note: Optional[str] = "Acknowledged by operator"


class CreateTicketRequest(BaseModel):
    system_type: str = "jira" # jira, servicenow, or itsm_webhook
    project_key: Optional[str] = "INC" # Jira Project Key or ServiceNow Category
    issue_type: Optional[str] = "Incident" # Jira Issue Type or ServiceNow Category
    urgency: Optional[str] = "High" # High, Medium, Low
    summary: Optional[str] = None
    description: Optional[str] = None


class TicketSyncResponse(BaseModel):
    alert_id: uuid.UUID
    ticket_id: str
    ticket_system: str
    ticket_status: str
    ticket_url: Optional[str] = None
    synced_at: datetime


class TicketingWebhookCallback(BaseModel):
    alert_id: Optional[uuid.UUID] = None
    ticket_id: str
    ticket_status: str
    notes: Optional[str] = None

