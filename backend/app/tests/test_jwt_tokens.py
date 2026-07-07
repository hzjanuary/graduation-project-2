"""Tests for JWT token utilities."""

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import jwt
import pytest

from app.auth import (
    TokenDecodeError,
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_token,
)
from app.auth.tokens import create_token
from app.config import get_settings


@pytest.fixture(autouse=True)
def reset_settings_cache(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Use deterministic JWT settings for token tests."""
    monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key-with-at-least-32-bytes")
    monkeypatch.setenv("JWT_ALGORITHM", "HS256")
    monkeypatch.setenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30")
    monkeypatch.setenv("REFRESH_TOKEN_EXPIRE_DAYS", "7")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_create_access_token_can_be_decoded() -> None:
    token = create_access_token("user-123")

    payload = decode_token(token, expected_token_type="access")

    assert payload.sub == "user-123"
    assert payload.token_type == "access"
    assert payload.exp > payload.iat
    assert payload.iat.tzinfo is not None
    assert payload.exp.tzinfo is not None


def test_create_refresh_token_can_be_decoded() -> None:
    token = create_refresh_token("user-123")

    payload = decode_token(token, expected_token_type="refresh")

    assert payload.sub == "user-123"
    assert payload.token_type == "refresh"
    assert payload.exp > payload.iat


def test_verify_token_returns_payload_for_valid_token() -> None:
    token = create_access_token("user-123")

    payload = verify_token(token, expected_token_type="access")

    assert payload is not None
    assert payload.sub == "user-123"


def test_verify_token_returns_none_for_invalid_token() -> None:
    assert verify_token("not-a-valid-token") is None


def test_decode_token_raises_for_invalid_token() -> None:
    with pytest.raises(TokenDecodeError):
        decode_token("not-a-valid-token")


def test_verify_token_returns_none_for_expired_token() -> None:
    token = create_token(
        subject="user-123",
        token_type="access",
        expires_delta=timedelta(seconds=-1),
    )

    assert verify_token(token, expected_token_type="access") is None


def test_access_token_rejected_when_refresh_expected() -> None:
    token = create_access_token("user-123")

    assert verify_token(token, expected_token_type="refresh") is None


def test_refresh_token_rejected_when_access_expected() -> None:
    token = create_refresh_token("user-123")

    assert verify_token(token, expected_token_type="access") is None


def test_token_signature_is_verified(monkeypatch: pytest.MonkeyPatch) -> None:
    token = create_access_token("user-123")
    monkeypatch.setenv("JWT_SECRET_KEY", "different-secret-key-with-32-plus-bytes")
    get_settings.cache_clear()

    assert verify_token(token, expected_token_type="access") is None


def test_token_uses_configured_expiration() -> None:
    token = create_access_token("user-123")
    settings = get_settings()

    raw_payload = jwt.decode(
        token,
        settings.jwt_secret_key,
        algorithms=[settings.jwt_algorithm],
    )
    issued_at = datetime.fromtimestamp(raw_payload["iat"], UTC)
    expires_at = datetime.fromtimestamp(raw_payload["exp"], UTC)

    assert expires_at - issued_at == timedelta(
        minutes=settings.access_token_expire_minutes,
    )
