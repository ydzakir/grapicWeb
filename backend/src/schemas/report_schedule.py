import uuid
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class ReportScheduleCreate(BaseModel):
    name: str = Field(..., min_length=3, max_length=128)
    frequency: str = Field("weekly", pattern="^(weekly|monthly|daily)$")
    report_type: str = Field("weekly", pattern="^(weekly|monthly)$")
    export_format: str = Field("pdf", pattern="^(pdf|excel|both)$")
    recipients: List[str] = Field(..., min_items=1)
    is_enabled: bool = True


class ReportScheduleUpdate(BaseModel):
    name: Optional[str] = None
    frequency: Optional[str] = Field(None, pattern="^(weekly|monthly|daily)$")
    report_type: Optional[str] = Field(None, pattern="^(weekly|monthly)$")
    export_format: Optional[str] = Field(None, pattern="^(pdf|excel|both)$")
    recipients: Optional[List[str]] = None
    is_enabled: Optional[bool] = None


class ReportScheduleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    frequency: str
    report_type: str
    export_format: str
    recipients: List[str]
    is_enabled: bool
    last_run_at: Optional[datetime] = None
    next_run_at: Optional[datetime] = None
    created_at: datetime
