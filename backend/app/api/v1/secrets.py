"""Secret Management API routes.

Prefix: /api/v1/secrets
Tags:   secrets

Security model:
  - Every endpoint requires authentication (get_current_user).
  - Users can only see/modify their OWN secrets.
  - GET /secrets/{id}/value is the ONLY endpoint that returns plaintext.
    It should always be accompanied by an audit log entry (Phase 7).
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import Settings
from app.api.deps import settings_provider
from app.db.session import get_db
from app.models.user import User
from app.schemas.secrets import (
    CategoryCreate,
    CategoryResponse,
    SecretCreate,
    SecretListResponse,
    SecretSummary,
    SecretUpdate,
    SecretValueResponse,
    SecretVersionResponse,
)
from app.services.secrets import (
    SecretError,
    SecretNotFoundError,
    SecretPermissionError,
    create_category,
    create_secret,
    delete_secret,
    get_secret_metadata,
    get_secret_value,
    list_categories,
    list_secret_versions,
    list_secrets,
    update_secret,
)
from app.services.audit import (
    log_secret_create,
    log_secret_read,
)

router = APIRouter(prefix="/secrets", tags=["secrets"])


def _client_ip(request: Request) -> str | None:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return None


def _user_agent(request: Request) -> str | None:
    return request.headers.get("User-Agent")


# ---------------------------------------------------------------------------
# Category endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/categories",
    response_model=CategoryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a secret category",
)
def create_category_endpoint(
    payload: CategoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CategoryResponse:
    try:
        cat = create_category(db, payload.name, payload.description, current_user)
    except SecretError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return CategoryResponse.model_validate(cat)


@router.get(
    "/categories",
    response_model=list[CategoryResponse],
    summary="List your categories",
)
def list_categories_endpoint(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[CategoryResponse]:
    cats = list_categories(db, current_user)
    return [CategoryResponse.model_validate(c) for c in cats]


# ---------------------------------------------------------------------------
# Secret CRUD endpoints
# ---------------------------------------------------------------------------


@router.post(
    "",
    response_model=SecretSummary,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new secret",
    description=(
        "Encrypts the plaintext `value` with a fresh AES-256-GCM DEK before storage. "
        "The plaintext never appears in the database."
    ),
)
def create_secret_endpoint(
    payload: SecretCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    settings: Settings = Depends(settings_provider),
) -> SecretSummary:
    try:
        secret = create_secret(db, payload, current_user, settings)
    except SecretError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    meta = get_secret_metadata(db, secret.id, current_user)
    log_secret_create(db, current_user.id, secret.id, secret.name, ip=_client_ip(request), ua=_user_agent(request))
    return SecretSummary(**meta)


@router.get(
    "",
    response_model=SecretListResponse,
    summary="List your secrets",
    description="Returns metadata only — never plaintext values. Supports search and category filter.",
)
def list_secrets_endpoint(
    search: str | None = Query(default=None, description="Search by name or description"),
    category_id: UUID | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SecretListResponse:
    result = list_secrets(db, current_user, search=search, category_id=category_id, page=page, page_size=page_size)
    return SecretListResponse(
        items=[SecretSummary(**item) for item in result["items"]],
        total=result["total"],
        page=result["page"],
        page_size=result["page_size"],
    )


@router.get(
    "/{secret_id}",
    response_model=SecretSummary,
    summary="Get secret metadata",
    description="Returns metadata for a single secret. Does NOT include the decrypted value.",
)
def get_secret_endpoint(
    secret_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SecretSummary:
    try:
        meta = get_secret_metadata(db, secret_id, current_user)
    except SecretNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except SecretPermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    return SecretSummary(**meta)


@router.get(
    "/{secret_id}/value",
    response_model=SecretValueResponse,
    summary="Retrieve the decrypted secret value",
    description=(
        "The ONLY endpoint that returns plaintext. Every call should be "
        "audit-logged (enforced in Phase 7). Requires ownership."
    ),
)
def get_secret_value_endpoint(
    secret_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    settings: Settings = Depends(settings_provider),
) -> SecretValueResponse:
    try:
        data = get_secret_value(db, secret_id, current_user, settings)
    except SecretNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except SecretPermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except SecretError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc
    # Audit every plaintext retrieval — this is the most sensitive action in the vault
    log_secret_read(db, current_user.id, secret_id, data["name"], ip=_client_ip(request), ua=_user_agent(request))
    return SecretValueResponse(**data)


@router.put(
    "/{secret_id}",
    response_model=SecretSummary,
    summary="Update a secret",
    description=(
        "Creates a new SecretVersion. Old versions are preserved. "
        "If no new `value` is supplied, the existing value is re-keyed under a fresh DEK."
    ),
)
def update_secret_endpoint(
    secret_id: UUID,
    payload: SecretUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    settings: Settings = Depends(settings_provider),
) -> SecretSummary:
    try:
        secret = update_secret(db, secret_id, payload, current_user, settings)
    except SecretNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except SecretPermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except SecretError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    meta = get_secret_metadata(db, secret.id, current_user)
    return SecretSummary(**meta)


@router.delete(
    "/{secret_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft-delete a secret",
    description=(
        "Marks the secret as deleted. Version history is preserved in the database. "
        "This operation is reversible by an admin (future feature)."
    ),
)
def delete_secret_endpoint(
    secret_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    try:
        delete_secret(db, secret_id, current_user)
    except SecretNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except SecretPermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@router.get(
    "/{secret_id}/versions",
    response_model=list[SecretVersionResponse],
    summary="List all versions of a secret",
    description="Returns version history metadata — never decrypted values.",
)
def list_versions_endpoint(
    secret_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[SecretVersionResponse]:
    try:
        versions = list_secret_versions(db, secret_id, current_user)
    except SecretNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except SecretPermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    return [SecretVersionResponse(**v) for v in versions]
