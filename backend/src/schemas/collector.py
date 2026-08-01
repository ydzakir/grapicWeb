import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from models.collector import TargetType


class CollectorTargetBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=128)
    target_type: TargetType
    host: str = Field(..., min_length=1, max_length=255)
    port: int = Field(..., ge=1, le=65535)
    credential_reference: str = Field(..., min_length=1, max_length=255)
    enabled: bool = True
    poll_interval_seconds: int = Field(default=60)
    metadata: dict[str, Any] = Field(default_factory=dict, alias="metadata_")

    model_config = ConfigDict(populate_by_name=True)

    @field_validator("target_type", mode="before")
    @classmethod
    def map_target_type(cls, v: Any) -> Any:
        if isinstance(v, str):
            val_lower = v.lower()
            if val_lower == "docker":
                return TargetType.DOCKER_TLS
            elif val_lower == "hyperv":
                return TargetType.WINRM
        return v

    @field_validator("poll_interval_seconds")
    @classmethod
    def validate_poll_interval(cls, v: int) -> int:
        if v < 30 or v > 60:
            raise ValueError("Status polling interval must be between 30 and 60 seconds.")
        return v


class CollectorTargetCreate(CollectorTargetBase):
    pass


class CollectorTargetUpdate(BaseModel):
    name: str | None = Field(None, min_length=2, max_length=128)
    target_type: TargetType | None = None
    host: str | None = Field(None, min_length=1, max_length=255)
    port: int | None = Field(None, ge=1, le=65535)
    credential_reference: str | None = Field(None, min_length=1, max_length=255)
    enabled: bool | None = None
    poll_interval_seconds: int | None = None
    metadata: dict[str, Any] | None = Field(None, alias="metadata_")

    model_config = ConfigDict(populate_by_name=True)

    @field_validator("target_type", mode="before")
    @classmethod
    def map_target_type(cls, v: Any) -> Any:
        if isinstance(v, str):
            val_lower = v.lower()
            if val_lower == "docker":
                return TargetType.DOCKER_TLS
            elif val_lower == "hyperv":
                return TargetType.WINRM
        return v

    @field_validator("poll_interval_seconds")
    @classmethod
    def validate_poll_interval(cls, v: int | None) -> int | None:
        if v is not None and (v < 30 or v > 60):
            raise ValueError("Status polling interval must be between 30 and 60 seconds.")
        return v


class CollectorTargetResponse(CollectorTargetBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class TestConnectionResponse(BaseModel):
    target_id: uuid.UUID
    success: bool
    message: str
