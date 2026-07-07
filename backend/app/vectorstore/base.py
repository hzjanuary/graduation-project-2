"""Vector store provider interface definitions."""

from typing import Protocol, runtime_checkable

from app.vectorstore.schemas import VectorPoint, VectorSearchResult


@runtime_checkable
class VectorStore(Protocol):
    """Implementation-agnostic async vector store provider contract."""

    async def create_collection(
        self,
        collection_name: str,
        vector_size: int,
    ) -> None:
        """Create a vector collection with the requested vector size."""

    async def collection_exists(self, collection_name: str) -> bool:
        """Return whether a collection exists."""

    async def upsert(
        self,
        collection_name: str,
        points: list[VectorPoint],
    ) -> None:
        """Insert or replace vector points in a collection."""

    async def search(
        self,
        collection_name: str,
        query_vector: list[float],
        limit: int = 10,
        filters: dict[str, object] | None = None,
    ) -> list[VectorSearchResult]:
        """Return vector search results for a query vector."""

    async def delete(
        self,
        collection_name: str,
        point_ids: list[str],
    ) -> None:
        """Delete points by id from a collection."""

    async def close(self) -> None:
        """Release provider resources."""
