from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.schemas.auth import RegisterRequest, TokenPairResponse
from app.security.hashing import hash_refresh_token
from app.security.passwords import hash_password, verify_password
from app.security.tokens import create_access_token, generate_refresh_token, refresh_token_expires_at
import zxcvbn
from datetime import timedelta


class AuthError(ValueError):
    pass


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == email.strip().lower()))


def register_user(db: Session, payload: RegisterRequest) -> User:
    if get_user_by_email(db, payload.email) is not None:
        raise AuthError("email already registered")

    # Enforce strict password entropy
    result = zxcvbn.zxcvbn(payload.password)
    if result["score"] < 3:
        raise AuthError("password too weak. Use a passphrase or standard password manager.")


    user = User(
        email=payload.email,
        password_hash=hash_password(payload.password),
        full_name=payload.full_name.strip(),
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, email: str, password: str) -> User:
    user = get_user_by_email(db, email)
    if user is None or not user.is_active:
        raise AuthError("invalid email or password")
        
    now = datetime.now(UTC)
    if user.locked_until and user.locked_until > now:
        raise AuthError("account locked due to too many failed attempts")

    if not verify_password(password, user.password_hash):
        user.failed_login_attempts += 1
        if user.failed_login_attempts >= 5:
            user.locked_until = now + timedelta(minutes=15)
        db.add(user)
        db.commit()
        raise AuthError("invalid email or password")

    user.failed_login_attempts = 0
    user.locked_until = None
    db.add(user)
    db.commit()
    return user


def issue_token_pair(db: Session, user: User, settings: Settings) -> TokenPairResponse:
    refresh_token = generate_refresh_token()
    refresh_token_record = RefreshToken(
        user_id=user.id,
        token_hash=hash_refresh_token(refresh_token, settings.jwt_secret_key),
        expires_at=refresh_token_expires_at(settings),
    )
    db.add(refresh_token_record)
    db.commit()

    return TokenPairResponse(
        access_token=create_access_token(user.id, settings),
        refresh_token=refresh_token,
        user=user,
    )


def refresh_tokens(db: Session, refresh_token: str, settings: Settings) -> TokenPairResponse:
    token_hash = hash_refresh_token(refresh_token, settings.jwt_secret_key)
    token_record = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
    now = datetime.now(UTC)
    if token_record is None or token_record.revoked_at is not None or token_record.expires_at <= now:
        raise AuthError("invalid refresh token")

    user = db.get(User, token_record.user_id)
    if user is None or not user.is_active:
        raise AuthError("invalid refresh token")

    token_record.revoked_at = now
    db.add(token_record)
    db.commit()
    return issue_token_pair(db, user, settings)


def logout(db: Session, refresh_token: str, settings: Settings) -> None:
    token_hash = hash_refresh_token(refresh_token, settings.jwt_secret_key)
    token_record = db.scalar(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
    if token_record is None or token_record.revoked_at is not None:
        return
    token_record.revoked_at = datetime.now(UTC)
    db.add(token_record)
    db.commit()
