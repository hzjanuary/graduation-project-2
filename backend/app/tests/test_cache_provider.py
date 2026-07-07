"""Tests for the cache provider interface."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from app.cache import CacheProvider


@dataclass(slots=True)
class CacheEntry:
    """Stored fake cache value."""

    value: str
    ttl_seconds: int | None = None


class InMemoryCacheProvider:
    """Test-only fake cache provider."""

    def __init__(self) -> None:
        self.entries: dict[str, CacheEntry] = {}
        self.closed = False

    async def get(self, key: str) -> str | None:
        entry = self.entries.get(key)
        return None if entry is None else entry.value

    async def set(
        self,
        key: str,
        value: str,
        ttl_seconds: int | None = None,
    ) -> None:
        self.entries[key] = CacheEntry(value=value, ttl_seconds=ttl_seconds)

    async def delete(self, key: str) -> None:
        self.entries.pop(key, None)

    async def exists(self, key: str) -> bool:
        return key in self.entries

    async def expire(self, key: str, ttl_seconds: int) -> None:
        entry = self.entries.get(key)
        if entry is not None:
            entry.ttl_seconds = ttl_seconds

    async def close(self) -> None:
        self.closed = True


def test_fake_cache_provider_satisfies_protocol() -> None:
    provider: CacheProvider = InMemoryCacheProvider()

    assert isinstance(provider, CacheProvider)


@pytest.mark.asyncio
async def test_cache_provider_get_set_exists_delete_behavior() -> None:
    provider: CacheProvider = InMemoryCacheProvider()

    assert await provider.get("missing") is None
    assert await provider.exists("missing") is False

    await provider.set("key", "value")

    assert await provider.get("key") == "value"
    assert await provider.exists("key") is True

    await provider.delete("key")

    assert await provider.get("key") is None
    assert await provider.exists("key") is False


@pytest.mark.asyncio
async def test_cache_provider_ttl_and_expire_behavior() -> None:
    provider = InMemoryCacheProvider()

    await provider.set("key", "value", ttl_seconds=60)
    await provider.expire("key", ttl_seconds=120)

    assert await provider.get("key") == "value"
    assert provider.entries["key"].ttl_seconds == 120


@pytest.mark.asyncio
async def test_cache_provider_close_behavior() -> None:
    provider = InMemoryCacheProvider()

    await provider.close()

    assert provider.closed is True
