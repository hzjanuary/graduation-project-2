"""Tests for infrastructure readiness checks."""

import asyncio
from collections.abc import Awaitable, Callable

import pytest

from app.config import Settings
from app.core.readiness import ReadinessChecker


async def healthy() -> bool:
    return True


async def unhealthy() -> bool:
    return False


async def raises_secret_error() -> bool:
    raise RuntimeError("postgresql://user:super-secret@example.test/db")


async def slow_check() -> bool:
    await asyncio.sleep(0.2)
    return True


def checker_with(
    *,
    postgres: Callable[[], Awaitable[bool]] = healthy,
    redis: Callable[[], Awaitable[bool]] = healthy,
    qdrant: Callable[[], Awaitable[bool]] = healthy,
    object_storage: Callable[[], Awaitable[bool]] = healthy,
    timeout: float = 2.0,
) -> ReadinessChecker:
    return ReadinessChecker(
        Settings(READINESS_TIMEOUT_SECONDS=timeout),
        postgres_check=postgres,
        redis_check=redis,
        qdrant_check=qdrant,
        object_storage_check=object_storage,
    )


def checker_with_failed(dependency: str) -> ReadinessChecker:
    if dependency == "postgres":
        return checker_with(postgres=unhealthy)
    if dependency == "redis":
        return checker_with(redis=unhealthy)
    if dependency == "qdrant":
        return checker_with(qdrant=unhealthy)
    if dependency == "object_storage":
        return checker_with(object_storage=unhealthy)
    raise AssertionError(f"unknown dependency: {dependency}")


@pytest.mark.asyncio
async def test_readiness_checker_returns_ok_for_all_dependencies() -> None:
    results = await checker_with().check_all()

    assert [result.name for result in results] == [
        "postgres",
        "redis",
        "qdrant",
        "object_storage",
    ]
    assert {result.status for result in results} == {"ok"}
    assert all(result.required for result in results)
    assert all(result.latency_ms is not None for result in results)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "dependency",
    ["postgres", "redis", "qdrant", "object_storage"],
)
async def test_readiness_checker_reports_failed_dependency(
    dependency: str,
) -> None:
    results = await checker_with_failed(dependency).check_all()

    failed = [result for result in results if result.status == "failed"]
    assert len(failed) == 1
    assert failed[0].name == dependency
    assert failed[0].message == "dependency check returned unhealthy"


@pytest.mark.asyncio
async def test_readiness_checker_sanitizes_exceptions() -> None:
    results = await checker_with(postgres=raises_secret_error).check_all()

    postgres = results[0]
    assert postgres.status == "failed"
    assert postgres.message == "dependency check failed"
    assert "super-secret" not in postgres.model_dump_json()
    assert "postgresql://" not in postgres.model_dump_json()


@pytest.mark.asyncio
async def test_readiness_checker_maps_timeout_safely() -> None:
    results = await checker_with(redis=slow_check, timeout=0.1).check_all()

    redis = results[1]
    assert redis.status == "failed"
    assert redis.message == "readiness check timed out"
