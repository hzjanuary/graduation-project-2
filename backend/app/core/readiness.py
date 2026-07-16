"""Dependency readiness checks for deployment health reporting."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from time import perf_counter

from sqlalchemy import text

from app.cache import create_redis_cache_provider
from app.config import Settings
from app.db.session import create_database_engine
from app.schemas import ReadinessDependencyStatus, ReadinessDependencyStatusValue
from app.storage.minio import MinIOStorageProvider
from app.vectorstore.qdrant import QdrantVectorStore

ReadinessCheckCallable = Callable[[], Awaitable[bool]]


class ReadinessChecker:
    """Run bounded, non-mutating infrastructure readiness checks."""

    def __init__(
        self,
        settings: Settings,
        *,
        postgres_check: ReadinessCheckCallable | None = None,
        redis_check: ReadinessCheckCallable | None = None,
        qdrant_check: ReadinessCheckCallable | None = None,
        object_storage_check: ReadinessCheckCallable | None = None,
    ) -> None:
        self._settings = settings
        self._checks: tuple[tuple[str, ReadinessCheckCallable], ...] = (
            ("postgres", postgres_check or self._check_postgres),
            ("redis", redis_check or self._check_redis),
            ("qdrant", qdrant_check or self._check_qdrant),
            ("object_storage", object_storage_check or self._check_object_storage),
        )

    async def check_all(self) -> list[ReadinessDependencyStatus]:
        """Return all dependency readiness results in deterministic order."""
        return [
            await self._run_check(name, check_callable)
            for name, check_callable in self._checks
        ]

    async def _run_check(
        self,
        name: str,
        check_callable: ReadinessCheckCallable,
    ) -> ReadinessDependencyStatus:
        started = perf_counter()
        status: ReadinessDependencyStatusValue
        message: str
        try:
            is_ready = await asyncio.wait_for(
                check_callable(),
                timeout=self._settings.readiness_timeout_seconds,
            )
        except TimeoutError:
            status = "failed"
            message = "readiness check timed out"
        except Exception:
            status = "failed"
            message = "dependency check failed"
        else:
            if is_ready:
                status = "ok"
                message = "ready"
            else:
                status = "failed"
                message = "dependency check returned unhealthy"

        latency_ms = round((perf_counter() - started) * 1000, 2)
        return ReadinessDependencyStatus(
            name=name,
            status=status,
            required=True,
            latency_ms=latency_ms,
            message=message,
        )

    async def _check_postgres(self) -> bool:
        engine = create_database_engine(self._settings.database_url, echo=False)
        try:
            async with engine.connect() as connection:
                await connection.execute(text("SELECT 1"))
        finally:
            await engine.dispose()
        return True

    async def _check_redis(self) -> bool:
        provider = create_redis_cache_provider(str(self._settings.redis_url))
        try:
            return await provider.health_check()
        finally:
            await provider.close()

    async def _check_qdrant(self) -> bool:
        vector_store = QdrantVectorStore.from_url(str(self._settings.qdrant_url))
        try:
            return await vector_store.health_check()
        finally:
            await vector_store.close()

    async def _check_object_storage(self) -> bool:
        storage = MinIOStorageProvider.from_settings(
            endpoint=self._settings.minio_endpoint,
            access_key=self._settings.minio_access_key,
            secret_key=self._settings.minio_secret_key,
            bucket_name=self._settings.minio_bucket_name,
        )
        try:
            return await storage.bucket_exists(self._settings.minio_bucket_name)
        finally:
            await storage.close()
