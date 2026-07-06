"""Tests for async database session configuration."""

import inspect

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.config import get_settings
from app.core.dependencies import provide_db_session
from app.db import (
    create_database_engine,
    create_session_factory,
    get_database_engine,
    get_session_factory,
)

DATABASE_URL = "postgresql+asyncpg://user:pass@postgres:5432/app"


@pytest.mark.asyncio
async def test_create_database_engine_uses_async_database_url() -> None:
    engine = create_database_engine(DATABASE_URL)

    try:
        assert isinstance(engine, AsyncEngine)
        assert engine.url.drivername == "postgresql+asyncpg"
        assert engine.url.host == "postgres"
        assert engine.url.database == "app"
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_create_session_factory_returns_async_session() -> None:
    engine = create_database_engine(DATABASE_URL)
    session_factory = create_session_factory(engine)

    try:
        async with session_factory() as session:
            assert isinstance(session, AsyncSession)
            assert session.sync_session.expire_on_commit is False
            assert session.sync_session.autoflush is False
    finally:
        await engine.dispose()


def test_cached_database_engine_uses_settings_database_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATABASE_URL", DATABASE_URL)
    get_settings.cache_clear()
    get_database_engine.cache_clear()
    get_session_factory.cache_clear()

    engine = get_database_engine()

    try:
        assert engine.url.render_as_string(hide_password=False) == DATABASE_URL
    finally:
        get_session_factory.cache_clear()
        get_database_engine.cache_clear()
        get_settings.cache_clear()


def test_fastapi_database_dependency_is_async_generator() -> None:
    assert inspect.isasyncgenfunction(provide_db_session)
