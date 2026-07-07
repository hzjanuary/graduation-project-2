"""Vector store provider exceptions."""


class VectorStoreError(RuntimeError):
    """Base error for vector store provider failures."""


class VectorStoreOperationError(VectorStoreError):
    """Raised when a vector store operation fails."""
