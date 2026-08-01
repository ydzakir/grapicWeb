import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from models.user import UserRole


class UserCreateRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=64)
    email: str = Field(..., min_length=5, max_length=255)
    password: str = Field(..., min_length=6)
    role: UserRole = UserRole.VIEWER
    custom_permissions: Optional[List[str]] = Field(default_factory=list) # e.g. ["nodes:write", "topology:edit"]
    allowed_group_scopes: Optional[List[str]] = Field(default_factory=lambda: ["*"]) # e.g. ["Jakarta-DC", "*"]
    is_active: bool = True


class UserUpdateRequest(BaseModel):
    email: Optional[str] = None
    password: Optional[str] = None
    role: Optional[UserRole] = None
    custom_permissions: Optional[List[str]] = None
    allowed_group_scopes: Optional[List[str]] = None
    is_active: Optional[bool] = None


class UserDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    username: str
    email: str
    role: UserRole
    is_active: bool
    custom_permissions: Dict[str, Any]
    allowed_group_scopes: Dict[str, Any]
    created_at: datetime


class PermissionDefinition(BaseModel):
    key: str
    label: str
    description: str


class PermissionsMatrixResponse(BaseModel):
    available_permissions: List[PermissionDefinition]
    default_role_mappings: Dict[str, List[str]]
