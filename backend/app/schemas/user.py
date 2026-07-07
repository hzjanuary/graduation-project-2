"""User response schemas."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict


class UserProfile(BaseModel):
    """Safe user profile returned by auth endpoints."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    full_name: str | None
    is_active: bool
    is_superuser: bool
