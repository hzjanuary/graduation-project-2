"""MinIO-backed object storage provider."""

from io import BytesIO

import anyio
from minio import Minio
from minio.error import S3Error

from app.config import get_settings
from app.storage.base import ObjectStorageProvider
from app.storage.exceptions import ObjectStorageOperationError
from app.storage.schemas import StoredObject

DEFAULT_CONTENT_TYPE = "application/octet-stream"


class MinIOStorageProvider(ObjectStorageProvider):
    """ObjectStorageProvider implementation backed by MinIO."""

    def __init__(self, client: Minio, default_bucket_name: str) -> None:
        self._client = client
        self._default_bucket_name = default_bucket_name

    @classmethod
    def from_settings(
        cls,
        endpoint: str,
        access_key: str,
        secret_key: str,
        bucket_name: str,
        secure: bool = False,
    ) -> "MinIOStorageProvider":
        """Create a provider from MinIO connection settings."""
        return cls(
            Minio(
                endpoint,
                access_key=access_key,
                secret_key=secret_key,
                secure=secure,
            ),
            default_bucket_name=bucket_name,
        )

    async def bucket_exists(self, bucket_name: str) -> bool:
        """Return whether a bucket exists."""
        try:
            return bool(
                await anyio.to_thread.run_sync(
                    self._client.bucket_exists,
                    bucket_name,
                ),
            )
        except S3Error as error:
            raise ObjectStorageOperationError(
                "MinIO bucket_exists operation failed",
            ) from error

    async def create_bucket(self, bucket_name: str) -> None:
        """Create a bucket when it does not exist."""
        try:
            bucket_exists = await anyio.to_thread.run_sync(
                self._client.bucket_exists,
                bucket_name,
            )
            if not bucket_exists:
                await anyio.to_thread.run_sync(
                    self._client.make_bucket,
                    bucket_name,
                )
        except S3Error as error:
            raise ObjectStorageOperationError(
                "MinIO create_bucket operation failed",
            ) from error

    async def upload_bytes(
        self,
        bucket_name: str,
        object_name: str,
        data: bytes,
        content_type: str | None = None,
    ) -> StoredObject:
        """Upload bytes to a bucket."""
        resolved_content_type = content_type or DEFAULT_CONTENT_TYPE
        try:
            await self.create_bucket(bucket_name)
            result = await anyio.to_thread.run_sync(
                lambda: self._client.put_object(
                    bucket_name,
                    object_name,
                    BytesIO(data),
                    length=len(data),
                    content_type=resolved_content_type,
                ),
            )
        except S3Error as error:
            raise ObjectStorageOperationError(
                "MinIO upload_bytes operation failed",
            ) from error

        return StoredObject(
            bucket_name=bucket_name,
            object_name=object_name,
            size=len(data),
            content_type=content_type,
            etag=result.etag,
        )

    async def download_bytes(self, bucket_name: str, object_name: str) -> bytes:
        """Download an object as bytes from a bucket."""
        try:
            response = await anyio.to_thread.run_sync(
                self._client.get_object,
                bucket_name,
                object_name,
            )
            try:
                return await anyio.to_thread.run_sync(response.read)
            finally:
                response.close()
                response.release_conn()
        except S3Error as error:
            raise ObjectStorageOperationError(
                "MinIO download_bytes operation failed",
            ) from error

    async def delete_object(self, bucket_name: str, object_name: str) -> None:
        """Delete an object from a bucket."""
        try:
            await anyio.to_thread.run_sync(
                self._client.remove_object,
                bucket_name,
                object_name,
            )
        except S3Error as error:
            raise ObjectStorageOperationError(
                "MinIO delete_object operation failed",
            ) from error

    async def object_exists(self, bucket_name: str, object_name: str) -> bool:
        """Return whether an object exists in a bucket."""
        try:
            await anyio.to_thread.run_sync(
                self._client.stat_object,
                bucket_name,
                object_name,
            )
        except S3Error as error:
            if error.code in {"NoSuchBucket", "NoSuchKey"}:
                return False
            raise ObjectStorageOperationError(
                "MinIO object_exists operation failed",
            ) from error
        return True

    async def close(self) -> None:
        """Release provider resources."""

    async def health_check(self) -> bool:
        """Return whether MinIO responds to a bucket existence check."""
        try:
            await anyio.to_thread.run_sync(
                self._client.bucket_exists,
                self._default_bucket_name,
            )
        except S3Error as error:
            raise ObjectStorageOperationError(
                "MinIO health check failed",
            ) from error
        return True


def create_minio_storage_provider() -> MinIOStorageProvider:
    """Create a MinIO object storage provider from settings."""
    settings = get_settings()
    return MinIOStorageProvider.from_settings(
        endpoint=settings.minio_endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        bucket_name=settings.minio_bucket_name,
    )
