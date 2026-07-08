"""Object storage provider interface definitions."""

from typing import Protocol, runtime_checkable

from app.storage.schemas import StoredObject


@runtime_checkable
class ObjectStorageProvider(Protocol):
    """Implementation-agnostic async object storage provider contract."""

    async def bucket_exists(self, bucket_name: str) -> bool:
        """Return whether a bucket exists."""

    async def create_bucket(self, bucket_name: str) -> None:
        """Create a bucket when it does not exist."""

    async def upload_bytes(
        self,
        bucket_name: str,
        object_name: str,
        data: bytes,
        content_type: str | None = None,
    ) -> StoredObject:
        """Upload bytes and return stored object metadata."""

    async def download_bytes(self, bucket_name: str, object_name: str) -> bytes:
        """Download an object as bytes."""

    async def delete_object(self, bucket_name: str, object_name: str) -> None:
        """Delete an object if it exists."""

    async def object_exists(self, bucket_name: str, object_name: str) -> bool:
        """Return whether an object exists."""

    async def close(self) -> None:
        """Release provider resources."""
