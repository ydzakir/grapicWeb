import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from models.node import ConnectionType, LifecycleStatus, NodeStatus, NodeType, ReviewStatus


class NodeBase(BaseModel):
    name: str = Field(..., max_length=255)
    type: NodeType
    parent_id: uuid.UUID | None = None
    os: str | None = None
    cpu_cores: int | None = Field(None, ge=1)
    ram_mb: int | None = Field(None, ge=1)
    disk_gb: float | None = Field(None, ge=0)
    ip_address: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class NodeCreate(NodeBase):
    pass


class NodeResponse(NodeBase):
    id: uuid.UUID
    status: NodeStatus
    review_status: ReviewStatus
    lifecycle_status: LifecycleStatus
    last_seen: datetime | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class NodeConnectionCreate(BaseModel):
    source_node_id: uuid.UUID
    target_node_id: uuid.UUID
    connection_type: ConnectionType = ConnectionType.DEPENDS_ON
    metadata: dict[str, Any] = Field(default_factory=dict)


class NodeConnectionResponse(NodeConnectionCreate):
    id: uuid.UUID
    created_at: datetime

    class Config:
        from_attributes = True
