import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_user, get_db, require_role
from core.audit import log_audit_event
from core.security import get_password_hash
from models.user import User, UserRole
from schemas.user import (
    PermissionDefinition,
    PermissionsMatrixResponse,
    UserCreateRequest,
    UserDetailResponse,
    UserUpdateRequest,
)

require_admin_role = require_role([UserRole.ADMIN])

router = APIRouter(prefix="/users", tags=["User Management & RBAC"])


SYSTEM_PERMISSIONS = [
    PermissionDefinition(key="nodes:read", label="Read Nodes", description="View infrastructure nodes and telemetry"),
    PermissionDefinition(key="nodes:write", label="Manage Nodes", description="Create, edit, approve, or delete nodes"),
    PermissionDefinition(key="topology:read", label="Read Topology", description="View topology graph canvas"),
    PermissionDefinition(key="topology:edit", label="Edit Topology", description="Create or delete links between nodes"),
    PermissionDefinition(key="alerts:read", label="Read Alerts", description="View incident alerts"),
    PermissionDefinition(key="alerts:ack", label="Acknowledge Alerts", description="Acknowledge or mute alerts"),
    PermissionDefinition(key="reports:export", label="Export Reports", description="Generate and download PDF/Excel reports"),
    PermissionDefinition(key="vault:manage", label="Manage Secrets", description="Encrypt/decrypt secret credentials"),
]


def _format_user_response(user: User) -> UserDetailResponse:
    perms_dict = user.custom_permissions if isinstance(user.custom_permissions, dict) else {"permissions": user.custom_permissions or []}
    scopes_dict = user.allowed_group_scopes if isinstance(user.allowed_group_scopes, dict) else {"scopes": user.allowed_group_scopes or ["*"]}

    return UserDetailResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        role=user.role,
        is_active=user.is_active,
        custom_permissions=perms_dict,
        allowed_group_scopes=scopes_dict,
        created_at=user.created_at,
    )


@router.get("/permissions/matrix", response_model=PermissionsMatrixResponse)
async def get_permissions_matrix(current_user: User = Depends(get_current_user)):
    """Retrieve system granular permissions matrix and default role mappings."""
    return PermissionsMatrixResponse(
        available_permissions=SYSTEM_PERMISSIONS,
        default_role_mappings={
            "admin": ["*"],
            "operator": ["nodes:read", "nodes:write", "topology:read", "topology:edit", "alerts:read", "alerts:ack", "reports:export"],
            "viewer": ["nodes:read", "topology:read", "alerts:read"],
        },
    )


@router.get("", response_model=List[UserDetailResponse])
async def list_users(
    role: Optional[UserRole] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin_role),
):
    """List all registered users with role filter (Admin only)."""
    stmt = select(User)
    if role:
        stmt = stmt.where(User.role == role)
    stmt = stmt.order_by(desc(User.created_at))

    res = await db.execute(stmt)
    users = list(res.scalars().all())
    return [_format_user_response(u) for u in users]


@router.post("", response_model=UserDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    body: UserCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin_role),
):
    """Create a new user account with custom granular permissions and scope (Admin only)."""
    # Check duplicate username or email
    stmt_check = select(User).where((User.username == body.username) | (User.email == body.email))
    res_check = await db.execute(stmt_check)
    if res_check.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username or email already registered",
        )

    hashed = get_password_hash(body.password)
    user = User(
        username=body.username,
        email=body.email,
        hashed_password=hashed,
        role=body.role,
        is_active=body.is_active,
        custom_permissions={"permissions": body.custom_permissions or []},
        allowed_group_scopes={"scopes": body.allowed_group_scopes or ["*"]},
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    await log_audit_event(
        db,
        actor_username=current_user.username,
        action="USER_CREATED",
        target=user.username,
        metadata={"role": user.role.value, "permissions": body.custom_permissions},
    )

    return _format_user_response(user)


@router.get("/{user_id}", response_model=UserDetailResponse)
async def get_user_detail(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin_role),
):
    """Get single user profile detail (Admin only)."""
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return _format_user_response(user)


@router.put("/{user_id}", response_model=UserDetailResponse)
async def update_user(
    user_id: uuid.UUID,
    body: UserUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin_role),
):
    """Update user role, active status, granular permissions, and scope (Admin only)."""
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if body.email is not None:
        user.email = body.email
    if body.password is not None and len(body.password) >= 6:
        user.hashed_password = get_password_hash(body.password)
    if body.role is not None:
        user.role = body.role
    if body.is_active is not None:
        user.is_active = body.is_active
    if body.custom_permissions is not None:
        user.custom_permissions = {"permissions": body.custom_permissions}
    if body.allowed_group_scopes is not None:
        user.allowed_group_scopes = {"scopes": body.allowed_group_scopes}

    await db.commit()
    await db.refresh(user)

    await log_audit_event(
        db,
        actor_username=current_user.username,
        action="USER_UPDATED",
        target=user.username,
        metadata_={"role": user.role.value},
    )

    return _format_user_response(user)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin_role),
):
    """Delete a user account (Admin only)."""
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if user.id == current_user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot delete your own admin account")

    await db.delete(user)
    await db.commit()

    await log_audit_event(
        db,
        actor_username=current_user.username,
        action="USER_DELETED",
        target=user.username,
    )
    return None
