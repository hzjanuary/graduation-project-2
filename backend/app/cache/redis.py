"""Redis-backed cache provider."""

from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.cache.base import CacheProvider
from app.cache.exceptions import CacheOperationError
from app.config import get_settings


class RedisCacheProvider(CacheProvider):
    """CacheProvider implementation backed by an async Redis client."""

    def __init__(self, client: Redis) -> None:
        self._client = client

    @classmethod
    def from_url(cls, redis_url: str) -> "RedisCacheProvider":
        """Create a provider from a Redis URL."""
        return cls(Redis.from_url(redis_url, decode_responses=True))

    async def get(self, key: str) -> str | None:
        """Return a cached string value, if present."""
        try:
            value = await self._client.get(key)
        except RedisError as error:
            raise CacheOperationError("Redis get operation failed") from error

        return value if isinstance(value, str) else None

    async def set(
        self,
        key: str,
        value: str,
        ttl_seconds: int | None = None,
    ) -> None:
        """Store a string value, optionally with a TTL."""
        try:
            await self._client.set(key, value, ex=ttl_seconds)
        except RedisError as error:
            raise CacheOperationError("Redis set operation failed") from error

    async def delete(self, key: str) -> None:
        """Remove a key if it exists."""
        try:
            await self._client.delete(key)
        except RedisError as error:
            raise CacheOperationError("Redis delete operation failed") from error

    async def exists(self, key: str) -> bool:
        """Return whether a key exists."""
        try:
            return bool(await self._client.exists(key))
        except RedisError as error:
            raise CacheOperationError("Redis exists operation failed") from error

    async def expire(self, key: str, ttl_seconds: int) -> None:
        """Set or replace the TTL for an existing key."""
        try:
            await self._client.expire(key, ttl_seconds)
        except RedisError as error:
            raise CacheOperationError("Redis expire operation failed") from error

    async def close(self) -> None:
        """Close the Redis client connection."""
        try:
            await self._client.aclose()
        except RedisError as error:
            raise CacheOperationError("Redis close operation failed") from error

    async def health_check(self) -> bool:
        """Return whether Redis responds to a ping."""
        try:
            return bool(await self._client.ping())
        except RedisError as error:
            raise CacheOperationError("Redis health check failed") from error


def create_redis_cache_provider(redis_url: str | None = None) -> RedisCacheProvider:
    """Create a Redis cache provider from settings or an explicit URL."""
    settings = get_settings()
    return RedisCacheProvider.from_url(redis_url or str(settings.redis_url))
