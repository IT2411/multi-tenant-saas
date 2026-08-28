from collections.abc import AsyncGenerator
from typing import Any

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import AsyncAdaptedQueuePool

from app.core.config import settings

logger = structlog.get_logger(__name__)


class Base(DeclarativeBase):
    """Declarative Base containing common metadata specifications."""

    pass


class DatabaseSessionManager:
    def __init__(self, host: str, engine_kwargs: dict[str, Any]) -> None:
        self._engine: AsyncEngine = create_async_engine(host, **engine_kwargs)
        self._session_maker: async_sessionmaker[AsyncSession] = async_sessionmaker(
            bind=self._engine,
            class_=AsyncSession,
            autocommit=False,
            autoflush=False,
            expire_on_commit=False,
        )

    async def close(self) -> None:
        await self._engine.dispose()
        logger.info("Database connection pool successfully drained.")

    @property
    def sessionmaker(self) -> async_sessionmaker[AsyncSession]:
        return self._session_maker

    @property
    def engine(self) -> AsyncEngine:
        return self._engine

    async def health_check(self) -> bool:
        async with self._session_maker() as session:
            result = await session.execute(text("SELECT 1"))
            scalar_val = result.scalar_one()
            return bool(scalar_val == 1)


engine_kwargs: dict[str, Any] = {
    "echo": False,
    "poolclass": AsyncAdaptedQueuePool,
    "pool_size": settings.DATABASE_POOL_SIZE,
    "max_overflow": settings.DATABASE_MAX_OVERFLOW,
    "pool_timeout": settings.DATABASE_POOL_TIMEOUT,
    "pool_recycle": settings.DATABASE_POOL_RECYCLE,
    "pool_pre_ping": True,
}

session_manager = DatabaseSessionManager(
    host=str(settings.SQLALCHEMY_DATABASE_URI),
    engine_kwargs=engine_kwargs,
)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency injector yielding a scoped async session per request lifecycle."""
    async with session_manager.sessionmaker() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
