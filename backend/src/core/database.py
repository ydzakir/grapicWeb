from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from core.config import settings


class Base(DeclarativeBase):
    pass


# Use sqlite in-memory for testing if set, otherwise PostgreSQL asyncpg or PgBouncer HA
if settings.ENVIRONMENT == "testing":
    DATABASE_URL = "sqlite+aiosqlite:///:memory:"
elif settings.HA_MODE_ENABLED:
    DATABASE_URL = settings.pgbouncer_async_database_url
else:
    DATABASE_URL = settings.async_database_url

engine_kwargs = {
    "echo": (settings.ENVIRONMENT == "development"),
    "future": True,
}

if settings.ENVIRONMENT != "testing":
    engine_kwargs.update({
        "pool_pre_ping": True,
        "pool_size": 10,
        "max_overflow": 20,
    })

engine = create_async_engine(
    DATABASE_URL,
    **engine_kwargs,
)


AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
