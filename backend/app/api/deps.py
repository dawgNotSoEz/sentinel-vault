from collections.abc import Generator
from uuid import UUID

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.db.session import get_db
from app.models.user import User
from app.security.tokens import TokenError, decode_access_token


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)

def settings_provider() -> Generator[Settings, None, None]:
    """FastAPI dependency wrapper for application settings."""
    yield get_settings()

def get_current_user(
    request: Request,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
    settings: Settings = Depends(settings_provider),
) -> User:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # Check cookie first, fallback to bearer header
    actual_token = request.cookies.get("access_token") or token
    if not actual_token:
        raise credentials_error

    try:
        payload = decode_access_token(actual_token, settings)
        user_id = UUID(str(payload["sub"]))
    except (TokenError, ValueError):
        raise credentials_error from None

    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise credentials_error
    return user
