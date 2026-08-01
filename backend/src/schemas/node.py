import uuid
from datetime import datetime
from typing import Any

from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field, field_validator

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
    metadata: dict[str, Any] = Field(default_factory=dict, validation_alias="metadata_")

    @field_validator("disk_gb", mode="before")
    @classmethod
    def convert_disk_gb(cls, v: Any) -> float | None:
        if v is None:
            return None
        if isinstance(v, (Decimal, int, float, str)):
            return float(v)
        return v

    @field_validator("metadata", mode="before")
    @classmethod
    def convert_metadata(cls, v: Any) -> dict[str, Any]:
        if v is None:
            return {}
        if isinstance(v, dict):
            return v
        return {}


class NodeCreate(NodeBase):
    pass


class NodeUpdate(BaseModel):
    name: str | None = Field(None, max_length=255)
    parent_id: uuid.UUID | None = None
    os: str | None = None
    cpu_cores: int | None = Field(None, ge=1)
    ram_mb: int | None = Field(None, ge=1)
    disk_gb: float | None = Field(None, ge=0)
    ip_address: str | None = None
    metadata: dict[str, Any] | None = None


class NodeResponse(NodeBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    status: NodeStatus
    review_status: ReviewStatus
    lifecycle_status: LifecycleStatus
    last_seen: datetime | None = None
    created_at: datetime
    updated_at: datetime


class PaginatedNodeResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[NodeResponse]


class NodeApproveRequest(BaseModel):
    name: str | None = Field(
        None,
        description="Optional custom host name if updating name upon approval to match convention",
    )


class NodeRejectRequest(BaseModel):
    reason: str | None = None


class NodeConnectionCreate(BaseModel):
    source_node_id: uuid.UUID
    target_node_id: uuid.UUID
    connection_type: ConnectionType = ConnectionType.DEPENDS_ON
    metadata: dict[str, Any] = Field(default_factory=dict)


class NodeConnectionResponse(NodeConnectionCreate):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime


# Data Center Schemas
class DataCenterCreate(BaseModel):
    name: str = Field(..., max_length=255)
    location: str | None = Field(None, max_length=255)
    metadata: dict[str, Any] = Field(default_factory=dict)


class DataCenterUpdate(BaseModel):
    name: str | None = Field(None, max_length=255)
    location: str | None = Field(None, max_length=255)
    metadata: dict[str, Any] | None = None


class DataCenterResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    type: NodeType = NodeType.DATA_CENTER
    status: NodeStatus
    review_status: ReviewStatus
    lifecycle_status: LifecycleStatus
    metadata: dict[str, Any] = Field(default_factory=dict, validation_alias="metadata_")
    created_at: datetime
    updated_at: datetime

    @field_validator("metadata", mode="before")
    @classmethod
    def convert_metadata(cls, v: Any) -> dict[str, Any]:
        if v is None:
            return {}
        if isinstance(v, dict):
            return v
        return {}


class AssignHostsRequest(BaseModel):
    host_ids: list[uuid.UUID]


# Topology Schemas
class TopologyNodeResponse(BaseModel):
    id: uuid.UUID
    name: str
    type: NodeType
    status: NodeStatus
    parent_id: uuid.UUID | None = None
    review_status: ReviewStatus
    lifecycle_status: LifecycleStatus
    ip_address: str | None = None
    os: str | None = None
    cpu_cores: int | None = None
    ram_mb: int | None = None
    disk_gb: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("disk_gb", mode="before")
    @classmethod
    def convert_disk_gb(cls, v: Any) -> float | None:
        if v is None:
            return None
        if isinstance(v, (Decimal, int, float, str)):
            return float(v)
        return v

    @field_validator("metadata", mode="before")
    @classmethod
    def convert_metadata(cls, v: Any) -> dict[str, Any]:
        if v is None:
            return {}
        if isinstance(v, dict):
            return v
        return {}


class TopologyEdgeResponse(BaseModel):
    id: str
    source: str
    target: str
    connection_type: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class TopologyGraphResponse(BaseModel):
    nodes: list[TopologyNodeResponse]
    edges: list[TopologyEdgeResponse]
