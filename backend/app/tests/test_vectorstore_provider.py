"""Tests for the vector store provider interface."""

from dataclasses import dataclass, field

import pytest

from app.vectorstore import VectorPoint, VectorSearchResult, VectorStore


@dataclass(slots=True)
class InMemoryCollection:
    """Test-only vector collection."""

    vector_size: int
    points: dict[str, VectorPoint] = field(default_factory=dict)


class InMemoryVectorStore:
    """Test-only fake vector store provider."""

    def __init__(self) -> None:
        self.collections: dict[str, InMemoryCollection] = {}
        self.closed = False

    async def create_collection(
        self,
        collection_name: str,
        vector_size: int,
    ) -> None:
        self.collections[collection_name] = InMemoryCollection(
            vector_size=vector_size,
        )

    async def collection_exists(self, collection_name: str) -> bool:
        return collection_name in self.collections

    async def upsert(
        self,
        collection_name: str,
        points: list[VectorPoint],
    ) -> None:
        collection = self.collections[collection_name]
        for point in points:
            collection.points[point.id] = point

    async def search(
        self,
        collection_name: str,
        query_vector: list[float],
        limit: int = 10,
        filters: dict[str, object] | None = None,
    ) -> list[VectorSearchResult]:
        collection = self.collections[collection_name]
        results = [
            VectorSearchResult(
                id=point.id,
                score=dot_product(query_vector, point.vector),
                payload=point.payload,
            )
            for point in collection.points.values()
            if payload_matches(point.payload, filters)
        ]
        return sorted(results, key=lambda result: result.score, reverse=True)[:limit]

    async def delete(
        self,
        collection_name: str,
        point_ids: list[str],
    ) -> None:
        collection = self.collections[collection_name]
        for point_id in point_ids:
            collection.points.pop(point_id, None)

    async def close(self) -> None:
        self.closed = True


def dot_product(left: list[float], right: list[float]) -> float:
    """Return a deterministic similarity score for fake search."""
    return sum(
        left_value * right_value
        for left_value, right_value in zip(left, right, strict=False)
    )


def payload_matches(
    payload: dict[str, object],
    filters: dict[str, object] | None,
) -> bool:
    """Return whether a payload contains all requested filter fields."""
    if filters is None:
        return True
    return all(payload.get(key) == value for key, value in filters.items())


def test_fake_vector_store_satisfies_protocol() -> None:
    vector_store: VectorStore = InMemoryVectorStore()

    assert isinstance(vector_store, VectorStore)


def test_vector_schemas_store_payloads() -> None:
    point = VectorPoint(
        id="point-1",
        vector=[0.1, 0.2, 0.3],
        payload={"source": "test"},
    )
    result = VectorSearchResult(
        id=point.id,
        score=0.95,
        payload=point.payload,
    )

    assert point.id == "point-1"
    assert point.vector == [0.1, 0.2, 0.3]
    assert result.payload["source"] == "test"


@pytest.mark.asyncio
async def test_vector_store_create_collection_and_collection_exists() -> None:
    vector_store: VectorStore = InMemoryVectorStore()

    assert await vector_store.collection_exists("documents") is False

    await vector_store.create_collection("documents", vector_size=3)

    assert await vector_store.collection_exists("documents") is True


@pytest.mark.asyncio
async def test_vector_store_upsert_search_and_delete_behavior() -> None:
    vector_store: VectorStore = InMemoryVectorStore()
    await vector_store.create_collection("documents", vector_size=3)

    await vector_store.upsert(
        "documents",
        [
            VectorPoint(
                id="point-1",
                vector=[1.0, 0.0, 0.0],
                payload={"tenant": "alpha"},
            ),
            VectorPoint(
                id="point-2",
                vector=[0.0, 1.0, 0.0],
                payload={"tenant": "beta"},
            ),
        ],
    )

    results = await vector_store.search(
        "documents",
        query_vector=[1.0, 0.0, 0.0],
        limit=1,
    )

    assert results == [
        VectorSearchResult(
            id="point-1",
            score=1.0,
            payload={"tenant": "alpha"},
        ),
    ]

    await vector_store.delete("documents", point_ids=["point-1"])
    results_after_delete = await vector_store.search(
        "documents",
        query_vector=[1.0, 0.0, 0.0],
    )

    assert [result.id for result in results_after_delete] == ["point-2"]


@pytest.mark.asyncio
async def test_vector_store_search_filters_payloads() -> None:
    vector_store: VectorStore = InMemoryVectorStore()
    await vector_store.create_collection("documents", vector_size=2)
    await vector_store.upsert(
        "documents",
        [
            VectorPoint(id="point-1", vector=[1.0, 0.0], payload={"tag": "public"}),
            VectorPoint(id="point-2", vector=[1.0, 0.0], payload={"tag": "private"}),
        ],
    )

    results = await vector_store.search(
        "documents",
        query_vector=[1.0, 0.0],
        filters={"tag": "private"},
    )

    assert [result.id for result in results] == ["point-2"]


@pytest.mark.asyncio
async def test_vector_store_close_behavior() -> None:
    vector_store = InMemoryVectorStore()

    await vector_store.close()

    assert vector_store.closed is True
