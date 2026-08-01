from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_user
from core.audit import log_audit_event
from core.config import settings
from core.database import get_db
from core.security import create_access_token
from core.sso.ldap_driver import LdapAuthDriver
from core.sso.oidc_driver import OidcAuthDriver
from models.user import User
from schemas.auth import LoginRequest, TokenResponse, UserResponse
from schemas.sso import (
    AuthProviderStatusResponse,
    LdapLoginRequest,
    OidcAuthorizeResponse,
    OidcCallbackRequest,
)
from services.auth_service import (
    authenticate_user,
    clear_failed_attempts,
    is_rate_limited,
    record_failed_attempt,
)
from services.sso_service import auto_provision_sso_user

router = APIRouter(prefix="/auth", tags=["Auth"])

ldap_driver = LdapAuthDriver()
oidc_driver = OidcAuthDriver()


@router.get("/providers", response_model=AuthProviderStatusResponse)
async def get_auth_providers():
    """Retrieve list of enabled authentication drivers (Local, LDAP, OIDC)."""
    active_providers = ["local"]
    if ldap_driver.is_enabled:
        active_providers.append("ldap")
    if oidc_driver.is_enabled:
        active_providers.append("oidc")

    return AuthProviderStatusResponse(
        local_enabled=True,
        ldap_enabled=ldap_driver.is_enabled,
        oidc_enabled=oidc_driver.is_enabled,
        providers=active_providers,
    )


async def _process_login(
    username_or_email: str,
    password: str,
    request: Request,
    response: Response,
    db: AsyncSession,
) -> TokenResponse:
    client_ip = request.client.host if request.client else "unknown"

    if is_rate_limited(client_ip, username_or_email):
        await log_audit_event(
            db,
            actor_username=username_or_email,
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

    user = await authenticate_user(db, username_or_email, password)
    if not user:
        record_failed_attempt(client_ip, username_or_email)
        await log_audit_event(
            db,
            actor_username=username_or_email,
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

    clear_failed_attempts(client_ip, username_or_email)
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
        metadata={"role": user.role.value, "auth_provider": "local"},
    )

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse.model_validate(user),
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    request: Request,
    response: Response,
    body: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """Authenticate user via JSON body, return JWT token."""
    return await _process_login(body.username_or_email, body.password, request, response, db)


@router.post("/token", response_model=TokenResponse)
async def token_endpoint(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """Authenticate user via Form Data or JSON body (OAuth2 standard token endpoint)."""
    content_type = request.headers.get("content-type", "")
    username = ""
    password = ""

    if "application/x-www-form-urlencoded" in content_type or "multipart/form-data" in content_type:
        form = await request.form()
        username = str(form.get("username", ""))
        password = str(form.get("password", ""))
    else:
        try:
            body = await request.json()
            username = body.get("username_or_email") or body.get("username", "")
            password = body.get("password", "")
        except Exception:
            pass

    if not username or not password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INVALID_INPUT", "message": "Username and password required"},
        )

    return await _process_login(username, password, request, response, db)


@router.post("/ldap/login", response_model=TokenResponse)
async def ldap_login(
    request: Request,
    response: Response,
    body: LdapLoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """Authenticate user against LDAP / Active Directory service."""
    client_ip = request.client.host if request.client else "unknown"

    ldap_user_info = await ldap_driver.authenticate(body.username, body.password)
    if not ldap_user_info:
        await log_audit_event(
            db,
            actor_username=body.username,
            action="ldap_login_failure",
            ip_address=client_ip,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "LDAP_AUTH_FAILED", "message": "LDAP / Active Directory authentication failed."},
        )

    # Auto-provision user account and map groups to role
    user = await auto_provision_sso_user(db, ldap_user_info)
    access_token = create_access_token(subject=str(user.id), role=user.role.value)

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
        action="ldap_login_success",
        ip_address=client_ip,
        metadata={"role": user.role.value, "groups": ldap_user_info.get("groups")},
    )

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse.model_validate(user),
    )


@router.get("/oidc/authorize", response_model=OidcAuthorizeResponse)
async def oidc_authorize():
    """Generates OpenID Connect (OIDC) authorization redirect URL."""
    auth_data = oidc_driver.get_authorization_url()
    return OidcAuthorizeResponse(**auth_data)


@router.post("/oidc/callback", response_model=TokenResponse)
async def oidc_callback(
    request: Request,
    response: Response,
    body: OidcCallbackRequest,
    db: AsyncSession = Depends(get_db),
):
    """Handles OIDC Authorization Code callback token exchange & auto-provisioning."""
    client_ip = request.client.host if request.client else "unknown"

    oidc_user_info = await oidc_driver.handle_callback(code=body.code)
    if not oidc_user_info:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "OIDC_AUTH_FAILED", "message": "OIDC Authorization code exchange failed."},
        )

    # Auto-provision user account
    user = await auto_provision_sso_user(db, oidc_user_info)
    access_token = create_access_token(subject=str(user.id), role=user.role.value)

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
        action="oidc_login_success",
        ip_address=client_ip,
        metadata={"role": user.role.value, "claims": oidc_user_info},
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

