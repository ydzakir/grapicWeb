import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from models.user import UserRole


class UserCreateRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=64)
    email: str = Field(..., min_length=5, max_length=255)
    password: str = Field(..., min_length=6)
    role: UserRole = UserRole.VIEWER
    custom_permissions: list[str] | None = Field(default_factory=list) # e.g. ["nodes:write", "topology:edit"]
    allowed_group_scopes: list[str] | None = Field(default_factory=lambda: ["*"]) # e.g. ["Jakarta-DC", "*"]
    is_active: bool = True


class UserUpdateRequest(BaseModel):
    email: str | None = None
    password: str | None = None
    role: UserRole | None = None
    custom_permissions: list[str] | None = None
    allowed_group_scopes: list[str] | None = None
    is_active: bool | None = None


class UserDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    username: str
    email: str
    role: UserRole
    is_active: bool
    custom_permissions: dict[str, Any]
    allowed_group_scopes: dict[str, Any]
    created_at: datetime


class PermissionDefinition(BaseModel):
    key: str
    label: str
    description: str


class PermissionsMatrixResponse(BaseModel):
    available_permissions: list[PermissionDefinition]
    default_role_mappings: dict[str, list[str]]
