from collections.abc import AsyncGenerator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.core.database import session_manager
from app.core.redis import redis_client
from app.main import app
from app.services.queue import JobQueueService
from app.websockets.hub import ws_hub

test_engine = create_async_engine(
    str(settings.SQLALCHEMY_DATABASE_URI),
    poolclass=NullPool,
)

TestingSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with TestingSessionLocal() as session:
        try:
            yield session
        finally:
            await session.rollback()
            await session.close()


@pytest_asyncio.fixture(scope="function", autouse=True)
async def _cleanup_pools() -> AsyncGenerator[None, None]:
    yield
    # 1. Clean SQLAlchemy Pool
    await session_manager.engine.dispose()

    # 2. Clean ARQ Pool
    if JobQueueService._pool is not None:
        await JobQueueService._pool.close()
        JobQueueService._pool = None

    # 3. Clean WebSocket Hub Sub Client
    if ws_hub._sub_client is not None:
        await ws_hub._sub_client.aclose()
        ws_hub._sub_client = None

    # 4. Flush Redis test db & close connection pool
    try:
        await redis_client.flushdb()
    finally:
        await redis_client.aclose()


@pytest_asyncio.fixture(scope="function")
async def client() -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac
