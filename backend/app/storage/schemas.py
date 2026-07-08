"""Object storage provider schemas."""

from pydantic import BaseModel, ConfigDict, Field


class StoredObject(BaseModel):
    """Metadata returned after an object is stored."""

    model_config = ConfigDict(frozen=True)

    bucket_name: str = Field(min_length=1)
    object_name: str = Field(min_length=1)
    size: int = Field(ge=0)
    content_type: str | None = None
    etag: str | None = None
