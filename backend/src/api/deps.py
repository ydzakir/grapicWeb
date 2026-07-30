import uuid
from collections.abc import Callable

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.security import decode_access_token
from models.user import User, UserRole

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


async def get_current_user_optional(
    request: Request,
    token: str | None = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User | None:
    """Extract user from HttpOnly cookie 'access_token' or Authorization header."""
    auth_token = token or request.cookies.get("access_token")
    if not auth_token:
        return None

    payload = decode_access_token(auth_token)
    if not payload or "sub" not in payload:
        return None

    try:
        user_uuid = uuid.UUID(payload["sub"])
    except (ValueError, TypeError):
        return None

    stmt = select(User).where(User.id == user_uuid)
    result = await db.execute(stmt)
    user = result.scalars().first()

    if not user or not user.is_active:
        return None

    return user


async def get_current_user(
    user: User | None = Depends(get_current_user_optional),
) -> User:
    """Enforce authenticated user requirement (HTTP 401 Unauthorized)."""
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "UNAUTHORIZED", "message": "Authentication required"},
        )
    return user


def require_role(allowed_roles: list[UserRole]) -> Callable[[User], User]:
    """Enforce Role-Based Access Control (HTTP 403 Forbidden)."""

    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "FORBIDDEN",
                    "message": (
                        f"Role '{current_user.role.value}' is not authorized to perform this action"
                    ),
                },
            )
        return current_user

    return role_checker
