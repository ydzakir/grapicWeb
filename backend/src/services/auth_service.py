import time
from collections import defaultdict

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.security import get_password_hash, verify_password
from models.user import User, UserRole

# Simple in-memory rate limiting for brute-force protection
# Key: (ip, username), Value: list of failed attempt timestamps
failed_attempts: dict[str, list[float]] = defaultdict(list)
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_DURATION_SECONDS = 900  # 15 minutes


def is_rate_limited(ip_address: str, username: str) -> bool:
    """Check if the IP or username has exceeded failed login attempts limit."""
    key = f"{ip_address}:{username}"
    now = time.time()
    # Filter attempts within lockout duration
    valid_attempts = [t for t in failed_attempts[key] if now - t < LOCKOUT_DURATION_SECONDS]
    failed_attempts[key] = valid_attempts
    return len(valid_attempts) >= MAX_FAILED_ATTEMPTS


def record_failed_attempt(ip_address: str, username: str) -> None:
    """Record a failed login attempt for rate limiting."""
    key = f"{ip_address}:{username}"
    failed_attempts[key].append(time.time())


def clear_failed_attempts(ip_address: str, username: str) -> None:
    """Clear failed attempts on successful login."""
    key = f"{ip_address}:{username}"
    if key in failed_attempts:
        del failed_attempts[key]


async def bootstrap_admin_user(db: AsyncSession) -> User:
    """Idempotently bootstrap initial admin user from settings if no admin exists."""
    stmt = select(User).where(User.role == UserRole.ADMIN)
    result = await db.execute(stmt)
    existing_admin = result.scalars().first()

    if existing_admin:
        return existing_admin

    # Check if user with admin email already exists
    admin_email = settings.BOOTSTRAP_ADMIN_EMAIL
    stmt_email = select(User).where(User.email == admin_email)
    result_email = await db.execute(stmt_email)
    user_by_email = result_email.scalars().first()

    if user_by_email:
        user_by_email.role = UserRole.ADMIN
        await db.flush()
        return user_by_email

    # Create new admin user
    hashed_pass = get_password_hash(settings.BOOTSTRAP_ADMIN_PASSWORD)
    admin_user = User(
        username="admin",
        email=admin_email,
        hashed_password=hashed_pass,
        role=UserRole.ADMIN,
        is_active=True,
    )
    db.add(admin_user)
    await db.flush()
    return admin_user


async def authenticate_user(
    db: AsyncSession, username_or_email: str, password: str
) -> User | None:
    """Authenticate a user by username or email and password."""
    stmt = select(User).where(
        or_(User.username == username_or_email, User.email == username_or_email)
    )
    result = await db.execute(stmt)
    user = result.scalars().first()

    if not user:
        return None
    if not user.is_active:
        return None
    if not verify_password(password, user.hashed_password):
        return None

    return user
