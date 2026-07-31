import uuid
from typing import Any

from pydantic import BaseModel, Field


class MetricDataPoint(BaseModel):
    timestamp: float = Field(..., description="Epoch timestamp in seconds")
    value: float = Field(..., description="Metric numeric value")


class MetricSeriesResponse(BaseModel):
    node_id: uuid.UUID
    metric_name: str
    range: str
    datapoints: list[MetricDataPoint]


class StatusDeltaMessage(BaseModel):
    event: str = "status_delta"
    node_id: str
    name: str
    type: str
    status: str
    last_seen: str | None = None
    timestamp: str
