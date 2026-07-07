"""Cache provider interfaces."""

from app.cache.base import CacheProvider
from app.cache.exceptions import CacheError, CacheOperationError

__all__ = [
    "CacheError",
    "CacheOperationError",
    "CacheProvider",
]
