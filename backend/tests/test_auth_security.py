from uuid import uuid4

import pytest

from app.core.config import Settings
from app.security.hashing import hash_refresh_token
from app.security.passwords import hash_password, verify_password
from app.security.tokens import TokenError, create_access_token, decode_access_token, generate_refresh_token


def test_password_hashing_uses_argon2_and_verifies() -> None:
    password_hash = hash_password("correct horse battery staple")

    assert password_hash.startswith("$argon2")
    assert verify_password("correct horse battery staple", password_hash) is True
    assert verify_password("wrong password", password_hash) is False


def test_empty_password_is_rejected() -> None:
    with pytest.raises(ValueError):
        hash_password("")


def test_access_token_round_trip() -> None:
    settings = Settings(APP_ENV="test", JWT_SECRET_KEY="unit-test-secret-with-at-least-32-bytes")
    user_id = uuid4()

    token = create_access_token(user_id, settings)
    payload = decode_access_token(token, settings)

    assert payload["sub"] == str(user_id)
    assert payload["type"] == "access"


def test_invalid_access_token_is_rejected() -> None:
    settings = Settings(APP_ENV="test", JWT_SECRET_KEY="unit-test-secret-with-at-least-32-bytes")

    with pytest.raises(TokenError):
        decode_access_token("not-a-valid-token", settings)


def test_refresh_token_generation_and_hashing() -> None:
    token = generate_refresh_token()
    token_hash = hash_refresh_token(token, "secret")

    assert len(token) >= 32
    assert token_hash == hash_refresh_token(token, "secret")
    assert token_hash != token
    assert token_hash != hash_refresh_token(token, "different-secret")
