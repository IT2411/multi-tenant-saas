from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger(__name__)


class UnitOfWork:
    """Manages transactional boundaries and session lifecycle."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    @asynccontextmanager
    async def transaction(self) -> AsyncGenerator[None, None]:
        """Context manager guaranteeing atomic commit or rollback."""
        try:
            yield
            await self.session.commit()
        except Exception as exc:
            await self.session.rollback()
            logger.error("transaction_rollback_executed", error=str(exc))
            raise exc


class BaseService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.uow = UnitOfWork(session)
