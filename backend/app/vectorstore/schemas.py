"""Vector store shared schemas."""

from pydantic import BaseModel, Field


class VectorPoint(BaseModel):
    """Vector point persisted in a vector store collection."""

    id: str
    vector: list[float]
    payload: dict[str, object] = Field(default_factory=dict)


class VectorSearchResult(BaseModel):
    """Vector search result returned by a provider."""

    id: str
    score: float
    payload: dict[str, object] = Field(default_factory=dict)
