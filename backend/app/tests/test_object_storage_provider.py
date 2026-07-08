"""Tests for the object storage provider interface."""

from dataclasses import dataclass, field

import pytest

from app.storage import ObjectStorageProvider, StoredObject


@dataclass(slots=True)
class InMemoryStoredObject:
    """Test-only stored object."""

    data: bytes
    content_type: str


@dataclass(slots=True)
class InMemoryObjectStorageProvider:
    """Test-only fake object storage provider."""

    buckets: set[str] = field(default_factory=set)
    objects: dict[tuple[str, str], InMemoryStoredObject] = field(default_factory=dict)
    closed: bool = False

    async def bucket_exists(self, bucket_name: str) -> bool:
        return bucket_name in self.buckets

    async def create_bucket(self, bucket_name: str) -> None:
        self.buckets.add(bucket_name)

    async def upload_bytes(
        self,
        bucket_name: str,
        object_name: str,
        data: bytes,
        content_type: str | None = None,
    ) -> StoredObject:
        await self.create_bucket(bucket_name)
        self.objects[(bucket_name, object_name)] = InMemoryStoredObject(
            data=data,
            content_type=content_type or "application/octet-stream",
        )
        return StoredObject(
            bucket_name=bucket_name,
            object_name=object_name,
            size=len(data),
            content_type=content_type,
        )

    async def download_bytes(self, bucket_name: str, object_name: str) -> bytes:
        return self.objects[(bucket_name, object_name)].data

    async def delete_object(self, bucket_name: str, object_name: str) -> None:
        self.objects.pop((bucket_name, object_name), None)

    async def object_exists(self, bucket_name: str, object_name: str) -> bool:
        return (bucket_name, object_name) in self.objects

    async def close(self) -> None:
        self.closed = True


def test_fake_object_storage_provider_satisfies_protocol() -> None:
    provider: ObjectStorageProvider = InMemoryObjectStorageProvider()

    assert isinstance(provider, ObjectStorageProvider)


def test_stored_object_schema_records_metadata() -> None:
    stored_object = StoredObject(
        bucket_name="documents",
        object_name="rfqs/request.txt",
        size=12,
        content_type="text/plain",
        etag="abc",
    )

    assert stored_object.bucket_name == "documents"
    assert stored_object.object_name == "rfqs/request.txt"
    assert stored_object.size == 12
    assert stored_object.content_type == "text/plain"
    assert stored_object.etag == "abc"


@pytest.mark.asyncio
async def test_object_storage_bucket_create_upload_download_delete_behavior() -> None:
    provider: ObjectStorageProvider = InMemoryObjectStorageProvider()
    bucket_name = "documents"
    object_name = "rfqs/request.txt"

    assert await provider.bucket_exists(bucket_name) is False

    await provider.create_bucket(bucket_name)

    assert await provider.bucket_exists(bucket_name) is True
    assert await provider.object_exists(bucket_name, object_name) is False

    stored_object = await provider.upload_bytes(
        bucket_name,
        object_name,
        b"hello",
        content_type="text/plain",
    )

    assert stored_object.size == 5
    assert stored_object.content_type == "text/plain"
    assert await provider.object_exists(bucket_name, object_name) is True
    assert await provider.download_bytes(bucket_name, object_name) == b"hello"

    await provider.delete_object(bucket_name, object_name)

    assert await provider.object_exists(bucket_name, object_name) is False


@pytest.mark.asyncio
async def test_object_storage_close_behavior() -> None:
    provider = InMemoryObjectStorageProvider()

    await provider.close()

    assert provider.closed is True
