"""Tests for Argon2 password hashing utilities."""

from app.auth import hash_password, password_needs_rehash, verify_password


def test_hash_password_returns_argon2_hash() -> None:
    plain_password = "correct horse battery staple"

    password_hash = hash_password(plain_password)

    assert password_hash != plain_password
    assert password_hash.startswith("$argon2")


def test_same_password_produces_different_hashes() -> None:
    plain_password = "correct horse battery staple"

    first_hash = hash_password(plain_password)
    second_hash = hash_password(plain_password)

    assert first_hash != second_hash


def test_verify_password_accepts_correct_password() -> None:
    plain_password = "correct horse battery staple"
    password_hash = hash_password(plain_password)

    assert verify_password(plain_password, password_hash) is True


def test_verify_password_rejects_incorrect_password() -> None:
    password_hash = hash_password("correct horse battery staple")

    assert verify_password("incorrect password", password_hash) is False


def test_verify_password_rejects_invalid_hash_safely() -> None:
    assert verify_password("correct horse battery staple", "not-a-valid-hash") is False


def test_password_needs_rehash_accepts_current_hash() -> None:
    password_hash = hash_password("correct horse battery staple")

    assert password_needs_rehash(password_hash) is False


def test_password_needs_rehash_rejects_invalid_hash_safely() -> None:
    assert password_needs_rehash("not-a-valid-hash") is False
