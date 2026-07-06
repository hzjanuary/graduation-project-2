"""Application dependency helpers."""

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.db import get_db_session


def provide_settings() -> Settings:
    """Provide typed application settings for dependency injection."""
    return get_settings()


async def provide_db_session() -> AsyncIterator[AsyncSession]:
    """Provide a request-scoped async database session."""
    async for session in get_db_session():
        yield session
