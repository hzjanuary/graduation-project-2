"""Authentication service."""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import (
    TokenPayload,
    create_access_token,
    create_refresh_token,
    verify_password,
    verify_token,
)
from app.models import User
from app.repositories import UserRepository
from app.schemas import TokenResponse


class AuthenticationError(ValueError):
    """Raised when authentication fails."""


class AuthService:
    """Authentication use cases backed by the user repository."""

    def __init__(self, session: AsyncSession) -> None:
        self.user_repository = UserRepository(session)

    async def login(self, *, email: str, password: str) -> TokenResponse:
        """Authenticate a user and return access and refresh tokens."""
        user = await self.user_repository.get_by_email(email)
        if (
            user is None
            or not user.is_active
            or not verify_password(password, user.hashed_password)
        ):
            raise AuthenticationError("Invalid credentials")

        return self.create_token_response(str(user.id))

    async def refresh(self, refresh_token: str) -> TokenResponse:
        """Validate a refresh token and return a new token pair."""
        payload = self.verify_payload(refresh_token, expected_token_type="refresh")
        user = await self.get_active_user(payload.sub)
        return self.create_token_response(str(user.id))

    async def get_current_user(self, access_token: str) -> User:
        """Return the active user identified by an access token."""
        payload = self.verify_payload(access_token, expected_token_type="access")
        return await self.get_active_user(payload.sub)

    def create_token_response(self, subject: str) -> TokenResponse:
        """Create a response containing access and refresh tokens."""
        return TokenResponse(
            access_token=create_access_token(subject),
            refresh_token=create_refresh_token(subject),
        )

    def verify_payload(
        self,
        token: str,
        *,
        expected_token_type: str,
    ) -> TokenPayload:
        """Verify a token and return its typed payload."""
        payload = verify_token(token, expected_token_type=expected_token_type)
        if payload is None:
            raise AuthenticationError("Invalid token")
        return payload

    async def get_active_user(self, subject: str) -> User:
        """Load an active user by token subject."""
        try:
            user_id = UUID(subject)
        except ValueError as error:
            raise AuthenticationError("Invalid token") from error

        user = await self.user_repository.get_with_roles(user_id)
        if user is None or not user.is_active:
            raise AuthenticationError("Invalid token")
        return user
