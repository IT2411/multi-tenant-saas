import json
from typing import Any, TypeVar

import structlog
from pydantic import BaseModel

from app.core.redis import redis_client

logger = structlog.get_logger(__name__)

T = TypeVar("T", bound=BaseModel)


class CacheService:
    """Async Redis cache manager implementing Cache-Aside with non-blocking key evictions."""

    DEFAULT_TTL_SECONDS = 300  # 5 minutes

    @staticmethod
    def build_key(namespace: str, *parts: str | Any) -> str:
        """Constructs standardized key: namespace:part1:part2."""
        clean_parts = [str(p).strip() for p in parts if p is not None]
        return f"{namespace}:{':'.join(clean_parts)}"

    @classmethod
    async def get(cls, key: str, schema: type[T]) -> T | None:
        """Retrieves a cached JSON record and parses it into a Pydantic schema."""
        try:
            cached_val = await redis_client.get(key)
            if not cached_val:
                return None
            data = json.loads(cached_val)
            return schema.model_validate(data)
        except Exception as exc:
            logger.warning("cache_get_error", key=key, error=str(exc))
            return None

    @classmethod
    async def set(
        cls,
        key: str,
        value: BaseModel | dict[str, Any],
        ttl_seconds: int = DEFAULT_TTL_SECONDS,
    ) -> None:
        """Stores a serialized payload in Redis with a TTL."""
        try:
            payload = value.model_dump_json() if isinstance(value, BaseModel) else json.dumps(value)
            await redis_client.set(key, payload, ex=ttl_seconds)
        except Exception as exc:
            logger.warning("cache_set_error", key=key, error=str(exc))

    @classmethod
    async def delete(cls, key: str) -> None:
        """Deletes a specific cache key."""
        try:
            await redis_client.delete(key)
        except Exception as exc:
            logger.warning("cache_delete_error", key=key, error=str(exc))

    @classmethod
    async def delete_pattern(cls, pattern: str) -> None:
        """Non-blocking batch invalidation using SCAN instead of blocking KEYS."""
        try:
            cursor = 0
            while True:
                cursor, keys = await redis_client.scan(cursor=cursor, match=pattern, count=100)
                if keys:
                    await redis_client.delete(*keys)
                if cursor == 0:
                    break
        except Exception as exc:
            logger.warning("cache_delete_pattern_error", pattern=pattern, error=str(exc))
