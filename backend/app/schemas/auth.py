"""Authentication request and response schemas."""

from pydantic import BaseModel

from app.schemas.user import UserProfile


class LoginRequest(BaseModel):
    """Login request payload."""

    email: str
    password: str


class RefreshRequest(BaseModel):
    """Refresh token request payload."""

    refresh_token: str


class TokenResponse(BaseModel):
    """Access and refresh token pair."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class CurrentUserResponse(BaseModel):
    """Current authenticated user response."""

    user: UserProfile


class LogoutResponse(BaseModel):
    """Stateless logout response."""

    success: bool
