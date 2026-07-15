from datetime import UTC, datetime, timedelta
from secrets import token_urlsafe
from typing import Any
from uuid import UUID

import jwt
from jwt import InvalidTokenError

from app.core.config import Settings

TOKEN_TYPE_ACCESS = "access"


class TokenError(ValueError):
    pass


def create_access_token(user_id: UUID | str, settings: Settings) -> str:
    now = datetime.now(UTC)
    expires_at = now + timedelta(minutes=settings.access_token_ttl_minutes)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "type": TOKEN_TYPE_ACCESS,
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str, settings: Settings) -> dict[str, Any]:
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except InvalidTokenError as exc:
        raise TokenError("invalid access token") from exc

    if payload.get("type") != TOKEN_TYPE_ACCESS:
        raise TokenError("invalid token type")
    if not payload.get("sub"):
        raise TokenError("missing subject")
    return payload


def generate_refresh_token() -> str:
    return token_urlsafe(48)


def refresh_token_expires_at(settings: Settings) -> datetime:
    return datetime.now(UTC) + timedelta(days=settings.refresh_token_ttl_days)
