"""Integration tests for the MinIO object storage provider."""

from collections.abc import AsyncIterator
from uuid import uuid4

import anyio
import pytest

from app.storage import (
    MinIOStorageProvider,
    ObjectStorageProvider,
    create_minio_storage_provider,
)


@pytest.fixture
async def minio_storage() -> AsyncIterator[tuple[MinIOStorageProvider, str]]:
    """Provide a MinIO storage provider with an isolated bucket."""
    provider = create_minio_storage_provider()
    bucket_name = f"test-storage-{uuid4().hex}"
    try:
        yield provider, bucket_name
    finally:
        if await provider.bucket_exists(bucket_name):
            objects = await anyio.to_thread.run_sync(
                lambda: list(
                    provider._client.list_objects(  # noqa: SLF001
                        bucket_name,
                        recursive=True,
                    ),
                ),
            )
            for stored_object in objects:
                await provider.delete_object(bucket_name, stored_object.object_name)
            await anyio.to_thread.run_sync(
                provider._client.remove_bucket,  # noqa: SLF001
                bucket_name,
            )
        await provider.close()


def object_name(name: str) -> str:
    """Return an isolated object name for this test provider."""
    return f"documents/{name}"


def test_minio_storage_provider_satisfies_protocol() -> None:
    provider: ObjectStorageProvider = create_minio_storage_provider()

    assert isinstance(provider, ObjectStorageProvider)


@pytest.mark.asyncio
async def test_minio_bucket_upload_download_exists_and_delete_behavior(
    minio_storage: tuple[MinIOStorageProvider, str],
) -> None:
    provider, bucket_name = minio_storage
    name = object_name("request.txt")

    assert await provider.bucket_exists(bucket_name) is False

    await provider.create_bucket(bucket_name)

    assert await provider.bucket_exists(bucket_name) is True
    assert await provider.object_exists(bucket_name, name) is False

    stored_object = await provider.upload_bytes(
        bucket_name,
        name,
        b"RFQ content",
        content_type="text/plain",
    )

    assert stored_object.bucket_name == bucket_name
    assert stored_object.object_name == name
    assert stored_object.size == len(b"RFQ content")
    assert stored_object.content_type == "text/plain"
    assert stored_object.etag is not None
    assert await provider.object_exists(bucket_name, name) is True
    assert await provider.download_bytes(bucket_name, name) == b"RFQ content"

    await provider.delete_object(bucket_name, name)

    assert await provider.object_exists(bucket_name, name) is False


@pytest.mark.asyncio
async def test_minio_health_check(
    minio_storage: tuple[MinIOStorageProvider, str],
) -> None:
    provider, _object_prefix = minio_storage

    assert await provider.health_check() is True


@pytest.mark.asyncio
async def test_minio_upload_creates_missing_bucket(
    minio_storage: tuple[MinIOStorageProvider, str],
) -> None:
    provider, bucket_name = minio_storage
    name = object_name("auto-create.txt")

    assert await provider.bucket_exists(bucket_name) is False

    stored_object = await provider.upload_bytes(bucket_name, name, b"small")

    assert stored_object.bucket_name == bucket_name
    assert stored_object.size == 5
    assert stored_object.content_type is None
    assert await provider.bucket_exists(bucket_name) is True
    assert await provider.download_bytes(bucket_name, name) == b"small"
