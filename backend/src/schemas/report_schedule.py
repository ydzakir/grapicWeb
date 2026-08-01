import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ReportScheduleCreate(BaseModel):
    name: str = Field(..., min_length=3, max_length=128)
    frequency: str = Field("weekly", pattern="^(weekly|monthly|daily)$")
    report_type: str = Field("weekly", pattern="^(weekly|monthly)$")
    export_format: str = Field("pdf", pattern="^(pdf|excel|both)$")
    recipients: list[str] = Field(..., min_items=1)
    is_enabled: bool = True


class ReportScheduleUpdate(BaseModel):
    name: str | None = None
    frequency: str | None = Field(None, pattern="^(weekly|monthly|daily)$")
    report_type: str | None = Field(None, pattern="^(weekly|monthly)$")
    export_format: str | None = Field(None, pattern="^(pdf|excel|both)$")
    recipients: list[str] | None = None
    is_enabled: bool | None = None


class ReportScheduleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    frequency: str
    report_type: str
    export_format: str
    recipients: list[str]
    is_enabled: bool
    last_run_at: datetime | None = None
    next_run_at: datetime | None = None
    created_at: datetime
