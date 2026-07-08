"""Object storage provider exceptions."""


class ObjectStorageError(RuntimeError):
    """Base error for object storage provider failures."""


class ObjectStorageOperationError(ObjectStorageError):
    """Raised when an object storage operation fails."""
