"""Integration tests for authentication API endpoints."""

from collections.abc import AsyncIterator
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import create_access_token, create_refresh_token, hash_password
from app.config import Settings, get_settings
from app.core.dependencies import provide_db_session
from app.db import create_database_engine, create_session_factory
from app.main import create_app
from app.models import User


@pytest.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    """Provide a rollback-only database session for auth API tests."""
    engine = create_database_engine(get_settings().database_url)
    session_factory = create_session_factory(engine)
    try:
        async with session_factory() as session:
            transaction = await session.begin()
            try:
                yield session
            finally:
                if transaction.is_active:
                    await transaction.rollback()
    finally:
        await engine.dispose()


@pytest.fixture
async def client(db_session: AsyncSession) -> AsyncIterator[AsyncClient]:
    """Provide an HTTP client with the database dependency overridden."""
    app = create_app(Settings())

    async def override_db_session() -> AsyncIterator[AsyncSession]:
        yield db_session

    app.dependency_overrides[provide_db_session] = override_db_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client
    app.dependency_overrides.clear()


def unique_email() -> str:
    """Return a unique test email address."""
    return f"user-{uuid4()}@example.test"


async def create_test_user(
    session: AsyncSession,
    *,
    email: str | None = None,
    password: str = "correct-password",
    is_active: bool = True,
) -> User:
    """Create a user directly in the database for auth tests."""
    user = User(
        email=email or unique_email(),
        hashed_password=hash_password(password),
        full_name="Auth Test User",
        is_active=is_active,
    )
    session.add(user)
    await session.flush()
    return user


async def login(
    client: AsyncClient,
    *,
    email: str,
    password: str,
) -> dict[str, str]:
    """Log in and return the token response body."""
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, dict)
    return data


@pytest.mark.asyncio
async def test_login_returns_tokens_for_valid_credentials(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    user = await create_test_user(db_session)

    data = await login(client, email=user.email, password="correct-password")

    assert data["access_token"]
    assert data["refresh_token"]
    assert data["token_type"] == "bearer"
    assert "hashed_password" not in data


@pytest.mark.asyncio
async def test_login_rejects_invalid_credentials(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    user = await create_test_user(db_session)

    response = await client.post(
        "/api/v1/auth/login",
        json={"email": user.email, "password": "wrong-password"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid credentials"


@pytest.mark.asyncio
async def test_login_rejects_inactive_user(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    user = await create_test_user(db_session, is_active=False)

    response = await client.post(
        "/api/v1/auth/login",
        json={"email": user.email, "password": "correct-password"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid credentials"


@pytest.mark.asyncio
async def test_refresh_returns_new_tokens_for_valid_refresh_token(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    user = await create_test_user(db_session)
    tokens = await login(client, email=user.email, password="correct-password")

    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )
    data = response.json()

    assert response.status_code == 200
    assert data["access_token"]
    assert data["refresh_token"]
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_refresh_rejects_access_token(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    user = await create_test_user(db_session)
    access_token = create_access_token(str(user.id))

    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": access_token},
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_me_returns_safe_user_profile(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    user = await create_test_user(db_session)
    tokens = await login(client, email=user.email, password="correct-password")

    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    data = response.json()

    assert response.status_code == 200
    assert data["user"]["id"] == str(user.id)
    assert data["user"]["email"] == user.email
    assert data["user"]["full_name"] == "Auth Test User"
    assert "hashed_password" not in data["user"]


@pytest.mark.asyncio
async def test_me_rejects_missing_token(client: AsyncClient) -> None:
    response = await client.get("/api/v1/auth/me")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_me_rejects_invalid_token(client: AsyncClient) -> None:
    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer not-a-valid-token"},
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_me_rejects_refresh_token(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    user = await create_test_user(db_session)
    refresh_token = create_refresh_token(str(user.id))

    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {refresh_token}"},
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_me_rejects_inactive_user(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    user = await create_test_user(db_session, is_active=False)
    access_token = create_access_token(str(user.id))

    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_logout_returns_success(client: AsyncClient) -> None:
    response = await client.post("/api/v1/auth/logout")

    assert response.status_code == 200
    assert response.json() == {"success": True}
