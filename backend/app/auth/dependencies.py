"""Authentication dependencies."""

from typing import Annotated, NoReturn

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import provide_db_session
from app.models import User
from app.services import AuthenticationError, AuthService

DbSessionDependency = Annotated[AsyncSession, Depends(provide_db_session)]

bearer_scheme = HTTPBearer(auto_error=False)
BearerCredentialsDependency = Annotated[
    HTTPAuthorizationCredentials | None,
    Depends(bearer_scheme),
]


async def get_current_user(
    credentials: BearerCredentialsDependency,
    session: DbSessionDependency,
) -> User:
    """Return the currently authenticated active user."""
    if credentials is None:
        raise_authentication_error()

    auth_service = AuthService(session)
    try:
        return await auth_service.get_current_user(credentials.credentials)
    except AuthenticationError:
        raise_authentication_error()


def raise_authentication_error() -> NoReturn:
    """Raise a generic HTTP 401 authentication error."""
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
