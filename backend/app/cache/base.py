"""Cache provider interface definitions."""

from typing import Protocol, runtime_checkable


@runtime_checkable
class CacheProvider(Protocol):
    """Implementation-agnostic async cache provider contract."""

    async def get(self, key: str) -> str | None:
        """Return the cached value for a key, if present."""

    async def set(
        self,
        key: str,
        value: str,
        ttl_seconds: int | None = None,
    ) -> None:
        """Store a string value, optionally with a TTL in seconds."""

    async def delete(self, key: str) -> None:
        """Remove a key if it exists."""

    async def exists(self, key: str) -> bool:
        """Return whether a key exists."""

    async def expire(self, key: str, ttl_seconds: int) -> None:
        """Set or replace the TTL for an existing key."""

    async def close(self) -> None:
        """Release provider resources."""
