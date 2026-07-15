import pytest
from pydantic import ValidationError

from app.schemas.auth import LoginRequest, RegisterRequest


def test_register_request_normalizes_email() -> None:
    payload = RegisterRequest(
        email="  USER@Example.COM ",
        password="very-secure-password",
        full_name="Test User",
    )

    assert payload.email == "user@example.com"


def test_register_request_rejects_short_password() -> None:
    with pytest.raises(ValidationError):
        RegisterRequest(email="user@example.com", password="short", full_name="Test User")


def test_login_request_normalizes_email() -> None:
    payload = LoginRequest(email=" USER@Example.COM ", password="password")

    assert payload.email == "user@example.com"
