from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_user
from core.audit import log_audit_event
from core.config import settings
from core.database import get_db
from core.security import create_access_token
from models.user import User
from schemas.auth import LoginRequest, TokenResponse, UserResponse
from services.auth_service import (
    authenticate_user,
    clear_failed_attempts,
    is_rate_limited,
    record_failed_attempt,
)

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/login", response_model=TokenResponse)
async def login(
    request: Request,
    response: Response,
    body: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """Authenticate user, return JWT, set secure HttpOnly cookie, and log audit event."""
    client_ip = request.client.host if request.client else "unknown"

    if is_rate_limited(client_ip, body.username_or_email):
        await log_audit_event(
            db,
            actor_username=body.username_or_email,
            action="login_blocked_rate_limit",
            ip_address=client_ip,
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "code": "RATE_LIMITED",
                "message": "Too many failed login attempts. Please try again later.",
            },
        )

    user = await authenticate_user(db, body.username_or_email, body.password)
    if not user:
        record_failed_attempt(client_ip, body.username_or_email)
        await log_audit_event(
            db,
            actor_username=body.username_or_email,
            action="login_failure",
            ip_address=client_ip,
            metadata={"reason": "invalid_credentials"},
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "INVALID_CREDENTIALS",
                "message": "Invalid username or password",
            },
        )

    clear_failed_attempts(client_ip, body.username_or_email)
    access_token = create_access_token(subject=str(user.id), role=user.role.value)

    # Set secure HttpOnly cookie
    is_prod = settings.ENVIRONMENT == "production"
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=is_prod,
        samesite="lax",
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )

    await log_audit_event(
        db,
        actor_username=user.username,
        action="login_success",
        ip_address=client_ip,
        metadata={"role": user.role.value},
    )

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse.model_validate(user),
    )


@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(
    request: Request,
    response: Response,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Log out user, clear cookie, and record audit event."""
    client_ip = request.client.host if request.client else "unknown"
    response.delete_cookie(key="access_token", httponly=True)

    await log_audit_event(
        db,
        actor_username=current_user.username,
        action="logout",
        ip_address=client_ip,
    )
    return {"message": "Successfully logged out"}


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """Return currently authenticated user information."""
    return UserResponse.model_validate(current_user)
