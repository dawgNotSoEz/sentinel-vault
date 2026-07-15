"""Auth API routes — Phase 3 + Phase 7 audit integration.

Every security-sensitive action (register, login, logout, refresh) now emits
an immutable audit log entry via the audit service.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, settings_provider
from app.core.config import Settings
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    RegisterRequest,
    TokenPairResponse,
    UserResponse,
)
from app.services.audit import log_auth_login, log_auth_login_failed, log_auth_logout, log_auth_register
from app.services.auth import AuthError, authenticate_user, issue_token_pair, logout, refresh_tokens, register_user

router = APIRouter(prefix="/auth", tags=["authentication"])


def _client_ip(request: Request) -> str | None:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return None


def _user_agent(request: Request) -> str | None:
    return request.headers.get("User-Agent")


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, request: Request, db: Session = Depends(get_db)) -> User:
    try:
        user = register_user(db, payload)
    except AuthError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    log_auth_register(db, user.id, ip=_client_ip(request), ua=_user_agent(request))
    return user


@router.post("/login", response_model=TokenPairResponse)
def login(
    payload: LoginRequest,
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(settings_provider),
) -> TokenPairResponse:
    try:
        user = authenticate_user(db, payload.email, payload.password)
        tokens = issue_token_pair(db, user, settings)
    except AuthError as exc:
        log_auth_login_failed(db, payload.email, ip=_client_ip(request), ua=_user_agent(request))
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    log_auth_login(db, user.id, ip=_client_ip(request), ua=_user_agent(request))
    return tokens


@router.post("/refresh", response_model=TokenPairResponse)
def refresh(
    payload: RefreshRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(settings_provider),
) -> TokenPairResponse:
    try:
        return refresh_tokens(db, payload.refresh_token, settings)
    except AuthError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout_current_session(
    payload: LogoutRequest,
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(settings_provider),
    current_user: User = Depends(get_current_user),
) -> None:
    logout(db, payload.refresh_token, settings)
    log_auth_logout(db, current_user.id, ip=_client_ip(request), ua=_user_agent(request))


@router.get("/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)) -> User:
    return current_user
