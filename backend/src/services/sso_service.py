import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.security import get_password_hash
from models.audit import AuditLog
from models.user import User, UserRole

logger = logging.getLogger("sso_service")


def map_external_groups_to_user_role(groups: List[str]) -> UserRole:
    """
    Maps external LDAP or OIDC groups to internal UserRole enum.
    """
    if not groups:
        return UserRole.VIEWER

    clean_groups = [str(g).lower() for g in groups]

    # Admin group patterns
    admin_patterns = ["domain admin", "administrator", "global admin", "infra-admin", "superadmin"]
    for g in clean_groups:
        if any(pat in g for pat in admin_patterns):
            return UserRole.ADMIN

    # Operator group patterns
    operator_patterns = ["infra op", "devops", "operator", "system engineer", "sysadmin"]
    for g in clean_groups:
        if any(pat in g for pat in operator_patterns):
            return UserRole.OPERATOR

    return UserRole.VIEWER


async def auto_provision_sso_user(
    db: AsyncSession,
    sso_user_info: Dict[str, Any],
) -> User:
    """
    Auto-provisions or updates user profile and role mapping from SSO/LDAP claims.
    """
    username = sso_user_info.get("username", "").strip()
    email = sso_user_info.get("email", "").strip()
    groups = sso_user_info.get("groups", [])
    provider = sso_user_info.get("provider", "sso")

    if not username:
        raise ValueError("SSO User Info missing required username attribute")

    # Map groups to internal UserRole
    mapped_role = map_external_groups_to_user_role(groups)

    # Check if user already exists
    stmt = select(User).where(or_(User.username == username, User.email == email))
    res = await db.execute(stmt)
    user = res.scalars().first()

    now = datetime.now(timezone.utc)

    if user:
        # Update role if mapped role is Admin/Operator
        if mapped_role in (UserRole.ADMIN, UserRole.OPERATOR) and user.role != UserRole.ADMIN:
            user.role = mapped_role
        user.is_active = True
        
        audit = AuditLog(
            actor_username=user.username,
            action="SSO_USER_LOGIN_SYNC",
            target=str(user.id),
            metadata_={"provider": provider, "role": user.role.value, "groups": groups},
        )
        db.add(audit)
    else:
        # Auto-provision new user account
        random_pass = f"SSO_{uuid.uuid4().hex[:12]}!"
        hashed_pass = get_password_hash(random_pass)

        user = User(
            username=username,
            email=email or f"{username}@sso.company.internal",
            hashed_password=hashed_pass,
            role=mapped_role,
            is_active=True,
        )
        db.add(user)

        audit = AuditLog(
            actor_username=username,
            action="SSO_USER_AUTO_PROVISIONED",
            target=username,
            metadata_={"provider": provider, "mapped_role": mapped_role.value, "groups": groups},
        )
        db.add(audit)

    await db.commit()
    await db.refresh(user)
    return user
