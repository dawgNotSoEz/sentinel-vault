"""Key Management API routes.

All endpoints here are admin-only — they expose the key hierarchy metadata
and allow rotation. No endpoint ever returns raw key material.

Prefix: /api/v1/keys
Tags:   key-management
"""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_current_user, settings_provider
from app.core.config import Settings
from app.db.session import get_db
from app.models.key import DataEncryptionKey, KeyEncryptionKey
from app.models.user import User
from app.schemas.keys import (
    DEKListResponse,
    DEKResponse,
    KEKListResponse,
    KEKResponse,
    RotateKEKResponse,
)
from app.services.key_management import (
    KeyManagementError,
    bootstrap_kek,
    get_active_kek,
    rotate_kek,
)
from app.services.rbac import PERM_KEYS_BOOTSTRAP, PERM_KEYS_READ, PERM_KEYS_ROTATE, require_permission

router = APIRouter(prefix="/keys", tags=["key-management"])


# ---------------------------------------------------------------------------
# KEK endpoints
# ---------------------------------------------------------------------------


@router.get(
    "/kek",
    response_model=KEKListResponse,
    summary="List all Key Encryption Keys",
    description=(
        "Returns metadata for every KEK in the hierarchy (active, retired, and compromised). "
        "Never returns raw key material. Admin only."
    ),
)
def list_keks(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(PERM_KEYS_READ)),
) -> KEKListResponse:
    rows = list(db.scalars(select(KeyEncryptionKey).order_by(KeyEncryptionKey.version.asc())))
    return KEKListResponse(
        items=[KEKResponse.model_validate(r) for r in rows],
        total=len(rows),
    )


@router.get(
    "/kek/active",
    response_model=KEKResponse,
    summary="Get the currently active KEK metadata",
)
def get_active_kek_info(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(PERM_KEYS_READ)),
) -> KEKResponse:
    kek = get_active_kek(db)
    if kek is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active KEK found. The vault may not be initialised yet.",
        )
    return KEKResponse.model_validate(kek)


@router.post(
    "/kek/bootstrap",
    response_model=KEKResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Bootstrap the initial KEK",
    description=(
        "Creates version-1 KEK if none exists. Idempotent — returns the existing active KEK "
        "if called again. Admin only."
    ),
)
def bootstrap_kek_endpoint(
    db: Session = Depends(get_db),
    settings: Settings = Depends(settings_provider),
    _: User = Depends(require_permission(PERM_KEYS_BOOTSTRAP)),
) -> KEKResponse:
    try:
        kek = bootstrap_kek(db, settings)
    except KeyManagementError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc
    return KEKResponse.model_validate(kek)


@router.post(
    "/kek/rotate",
    response_model=RotateKEKResponse,
    summary="Rotate the active KEK",
    description=(
        "Generates a new KEK, re-encrypts all DEKs under it, and retires the old KEK. "
        "This operation is atomic — on failure the old KEK remains active. Admin only."
    ),
)
def rotate_kek_endpoint(
    db: Session = Depends(get_db),
    settings: Settings = Depends(settings_provider),
    _: User = Depends(require_permission(PERM_KEYS_ROTATE)),
) -> RotateKEKResponse:
    # Count DEKs before rotation so we can report how many were re-encrypted
    old_kek = get_active_kek(db)
    if old_kek is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active KEK to rotate.",
        )
    dek_count = db.scalar(
        select(func.count()).where(DataEncryptionKey.kek_id == old_kek.id)
    ) or 0

    try:
        new_kek = rotate_kek(db, settings)
    except KeyManagementError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc

    return RotateKEKResponse(
        new_kek=KEKResponse.model_validate(new_kek),
        deks_re_encrypted=dek_count,
    )


# ---------------------------------------------------------------------------
# DEK endpoints
# ---------------------------------------------------------------------------


@router.get(
    "/dek",
    response_model=DEKListResponse,
    summary="List all Data Encryption Keys",
    description="Returns metadata only — never raw key bytes. Admin only.",
)
def list_deks(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(PERM_KEYS_READ)),
) -> DEKListResponse:
    rows = list(
        db.scalars(select(DataEncryptionKey).order_by(DataEncryptionKey.created_at.desc()))
    )
    return DEKListResponse(
        items=[DEKResponse.model_validate(r) for r in rows],
        total=len(rows),
    )


@router.get(
    "/dek/{dek_id}",
    response_model=DEKResponse,
    summary="Get a single DEK's metadata",
)
def get_dek(
    dek_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(PERM_KEYS_READ)),
) -> DEKResponse:
    dek = db.get(DataEncryptionKey, dek_id)
    if dek is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="DEK not found.")
    return DEKResponse.model_validate(dek)
