"""Integration tests for the Redis cache provider."""

from collections.abc import AsyncIterator
from uuid import uuid4

import pytest

from app.cache import CacheProvider, RedisCacheProvider, create_redis_cache_provider
from app.config import get_settings


@pytest.fixture
async def redis_provider() -> AsyncIterator[tuple[RedisCacheProvider, str]]:
    """Provide a Redis cache provider and clean isolated test keys."""
    provider = create_redis_cache_provider(str(get_settings().redis_url))
    key_prefix = f"test:cache:{uuid4()}:"
    try:
        yield provider, key_prefix
    finally:
        keys = await provider._client.keys(f"{key_prefix}*")  # noqa: SLF001
        if keys:
            await provider._client.delete(*keys)  # noqa: SLF001
        await provider.close()


def cache_key(key_prefix: str, key: str) -> str:
    """Return an isolated Redis key for this test provider."""
    return f"{key_prefix}{key}"


def test_redis_cache_provider_satisfies_protocol() -> None:
    provider: CacheProvider = create_redis_cache_provider(
        str(get_settings().redis_url),
    )

    assert isinstance(provider, CacheProvider)


@pytest.mark.asyncio
async def test_redis_cache_get_set_exists_delete_behavior(
    redis_provider: tuple[RedisCacheProvider, str],
) -> None:
    provider, key_prefix = redis_provider
    key = cache_key(key_prefix, "basic")

    assert await provider.get(key) is None
    assert await provider.exists(key) is False

    await provider.set(key, "value")

    assert await provider.get(key) == "value"
    assert await provider.exists(key) is True

    await provider.delete(key)

    assert await provider.get(key) is None
    assert await provider.exists(key) is False


@pytest.mark.asyncio
async def test_redis_cache_set_supports_ttl(
    redis_provider: tuple[RedisCacheProvider, str],
) -> None:
    provider, key_prefix = redis_provider
    key = cache_key(key_prefix, "ttl")

    await provider.set(key, "value", ttl_seconds=30)

    ttl = await provider._client.ttl(key)  # noqa: SLF001
    assert await provider.get(key) == "value"
    assert 0 < ttl <= 30


@pytest.mark.asyncio
async def test_redis_cache_expire_updates_ttl(
    redis_provider: tuple[RedisCacheProvider, str],
) -> None:
    provider, key_prefix = redis_provider
    key = cache_key(key_prefix, "expire")

    await provider.set(key, "value")
    await provider.expire(key, ttl_seconds=20)

    ttl = await provider._client.ttl(key)  # noqa: SLF001
    assert 0 < ttl <= 20


@pytest.mark.asyncio
async def test_redis_cache_health_check(
    redis_provider: tuple[RedisCacheProvider, str],
) -> None:
    provider, _key_prefix = redis_provider

    assert await provider.health_check() is True
