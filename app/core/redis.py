from datetime import UTC, datetime

import redis.asyncio as aioredis
import structlog

from app.core.config import settings

logger = structlog.get_logger(__name__)

# Initialize async Redis connection pool
redis_client = aioredis.from_url(
    str(settings.REDIS_URI),
    encoding="utf-8",
    decode_responses=True,
)


class TokenBlacklistService:
    """Manages revoked token identifiers (JTI) in Redis with automatic TTL expiration."""

    PREFIX = "token_blacklist:"

    @classmethod
    async def revoke_token(cls, jti: str, expires_at: datetime) -> None:
        """Stores token JTI in Redis until its expiration time."""
        now = datetime.now(UTC)
        ttl = int((expires_at - now).total_seconds())
        if ttl > 0:
            await redis_client.set(f"{cls.PREFIX}{jti}", "revoked", ex=ttl)
            logger.info("token_revoked", jti=jti, ttl_seconds=ttl)

    @classmethod
    async def is_token_revoked(cls, jti: str) -> bool:
        """Returns True if the token JTI has been revoked."""
        exists = await redis_client.exists(f"{cls.PREFIX}{jti}")
        return bool(exists == 1)
