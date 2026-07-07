"""Cache provider exceptions."""


class CacheError(RuntimeError):
    """Base error for cache provider failures."""


class CacheOperationError(CacheError):
    """Raised when a cache operation fails."""
