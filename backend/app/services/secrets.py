"""Secret Management Service — CRUD + envelope encryption.

Every secret value is encrypted with a fresh DEK before it's stored.
The plaintext never appears in the database — only the ciphertext, nonce,
and auth tag are persisted alongside the DEK reference.

Read path:
    SecretVersion.dek_id → DataEncryptionKey → KEK → Master Key
    → raw DEK → AES-256-GCM decrypt(ciphertext, nonce, auth_tag)
    → plaintext

Write path:
    plaintext → AES-256-GCM encrypt with fresh DEK
    → store ciphertext + nonce + auth_tag + dek_id in SecretVersion

Versioning:
    Each update creates a NEW SecretVersion with an incremented version
    number. Old versions are preserved for audit / rollback.

Soft delete:
    Deleting a secret sets Secret.deleted_at — versions are preserved.
    Listing queries filter out deleted secrets by default.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models.category import Category
from app.models.key import DataEncryptionKey
from app.models.secret import Secret, SecretVersion
from app.models.user import User
from app.schemas.secrets import SecretCreate, SecretUpdate
from app.security.crypto import EncryptedPayload, decrypt, encrypt
from app.services.key_management import (
    KeyManagementError,
    bootstrap_kek,
    decrypt_dek,
    generate_dek,
)

logger = logging.getLogger(__name__)


class SecretError(ValueError):
    """Domain error for secret management operations."""


class SecretNotFoundError(SecretError):
    """Raised when a secret cannot be found or has been deleted."""


class SecretPermissionError(SecretError):
    """Raised when a user lacks permission to access a secret."""


# ---------------------------------------------------------------------------
# Internal crypto helpers
# ---------------------------------------------------------------------------


def _encrypt_value(plaintext: str, raw_dek: bytes) -> tuple[bytes, bytes, bytes]:
    """Encrypt a secret value with the given DEK.

    Returns:
        (ciphertext, nonce, auth_tag)
    """
    payload = encrypt(plaintext.encode("utf-8"), raw_dek)
    return payload.ciphertext, payload.nonce, payload.auth_tag


def _decrypt_value(
    ciphertext: bytes,
    nonce: bytes,
    auth_tag: bytes,
    raw_dek: bytes,
) -> str:
    """Decrypt a secret value with the given DEK."""
    payload = EncryptedPayload(ciphertext=ciphertext, nonce=nonce, auth_tag=auth_tag)
    return decrypt(payload, raw_dek).decode("utf-8")


def _ensure_kek_exists(db: Session, settings: Settings) -> None:
    """Bootstrap a KEK if none exists yet (first-time setup)."""
    try:
        bootstrap_kek(db, settings)
    except KeyManagementError as exc:
        raise SecretError(f"Key management not ready: {exc}") from exc


# ---------------------------------------------------------------------------
# Category operations
# ---------------------------------------------------------------------------


def create_category(db: Session, name: str, description: str, user: User) -> Category:
    """Create a category owned by the current user."""
    existing = db.scalar(
        select(Category).where(
            Category.name == name.strip(),
            Category.created_by == user.id,
        )
    )
    if existing is not None:
        raise SecretError(f"Category '{name}' already exists.")
    cat = Category(name=name.strip(), description=description, created_by=user.id)
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return cat


def list_categories(db: Session, user: User) -> list[Category]:
    return list(
        db.scalars(
            select(Category)
            .where(Category.created_by == user.id)
            .order_by(Category.name.asc())
        )
    )


# ---------------------------------------------------------------------------
# Secret helpers
# ---------------------------------------------------------------------------


def _get_active_secret(db: Session, secret_id: UUID, user_id: UUID) -> Secret:
    """Load a non-deleted secret that belongs to the given user.

    Raises SecretNotFoundError if missing, deleted, or owned by someone else.
    """
    secret = db.get(Secret, secret_id)
    if secret is None or secret.deleted_at is not None:
        raise SecretNotFoundError(f"Secret {secret_id} not found.")
    if str(secret.created_by) != str(user_id):
        raise SecretPermissionError("You do not have access to this secret.")
    return secret


def _latest_version(db: Session, secret: Secret) -> SecretVersion:
    """Return the highest-version SecretVersion for a Secret."""
    sv = db.scalar(
        select(SecretVersion)
        .where(SecretVersion.secret_id == secret.id)
        .order_by(SecretVersion.version.desc())
        .limit(1)
    )
    if sv is None:
        raise SecretError(f"Secret {secret.id} has no versions — data integrity issue.")
    return sv


# ---------------------------------------------------------------------------
# Core CRUD
# ---------------------------------------------------------------------------


def create_secret(
    db: Session,
    payload: SecretCreate,
    user: User,
    settings: Settings,
) -> Secret:
    """Create a new Secret with version 1 encrypted under a fresh DEK.

    Steps:
      1. Ensure a KEK exists (bootstrap on first run).
      2. Generate a fresh DEK.
      3. Encrypt the plaintext value with the DEK.
      4. Persist Secret + SecretVersion in a single transaction.
    """
    _ensure_kek_exists(db, settings)

    # Validate category ownership if provided
    if payload.category_id is not None:
        cat = db.get(Category, payload.category_id)
        if cat is None or str(cat.created_by) != str(user.id):
            raise SecretError("Category not found or does not belong to you.")

    # Generate a unique DEK for this secret version
    dek, raw_dek = generate_dek(db, settings)

    # Encrypt the plaintext
    ciphertext, nonce, auth_tag = _encrypt_value(payload.value, raw_dek)

    # Persist
    secret = Secret(
        name=payload.name.strip(),
        description=payload.description,
        category_id=payload.category_id,
        created_by=user.id,
    )
    db.add(secret)
    db.flush()  # get secret.id before creating version

    version = SecretVersion(
        secret_id=secret.id,
        version=1,
        ciphertext=ciphertext,
        nonce=nonce,
        auth_tag=auth_tag,
        dek_id=dek.id,
        notes=payload.notes,
        metadata_json={"tags": payload.tags},
    )
    db.add(version)
    db.commit()
    db.refresh(secret)

    logger.info(
        "Secret created: id=%s name=%r user=%s", secret.id, secret.name, user.id
    )
    return secret


def get_secret_metadata(db: Session, secret_id: UUID, user: User) -> dict:
    """Return metadata for a secret (no decrypted value)."""
    secret = _get_active_secret(db, secret_id, user.id)
    sv = _latest_version(db, secret)
    return {
        "id": secret.id,
        "name": secret.name,
        "description": secret.description,
        "category_id": secret.category_id,
        "created_by": secret.created_by,
        "current_version": sv.version,
        "tags": sv.metadata_json.get("tags", []),
        "created_at": secret.created_at,
        "updated_at": secret.updated_at,
    }


def get_secret_value(
    db: Session,
    secret_id: UUID,
    user: User,
    settings: Settings,
) -> dict:
    """Decrypt and return the current value of a secret.

    This is the only path that returns plaintext — it should always be
    paired with an audit log entry by the caller.
    """
    secret = _get_active_secret(db, secret_id, user.id)
    sv = _latest_version(db, secret)

    dek = db.get(DataEncryptionKey, sv.dek_id)
    if dek is None:
        raise SecretError(f"DEK {sv.dek_id} not found — integrity issue.")

    raw_dek = decrypt_dek(dek, db, settings)
    plaintext = _decrypt_value(sv.ciphertext, sv.nonce, sv.auth_tag, raw_dek)

    return {
        "id": secret.id,
        "name": secret.name,
        "value": plaintext,
        "version": sv.version,
        "tags": sv.metadata_json.get("tags", []),
        "notes": sv.notes,
        "retrieved_at": datetime.now(UTC),
    }


def update_secret(
    db: Session,
    secret_id: UUID,
    payload: SecretUpdate,
    user: User,
    settings: Settings,
) -> Secret:
    """Update a secret — always creates a new SecretVersion.

    If `value` is not provided in the payload, the latest ciphertext is
    re-encrypted under a new DEK (re-key without exposing plaintext).
    If `value` IS provided, the new plaintext is encrypted fresh.
    """
    secret = _get_active_secret(db, secret_id, user.id)
    sv = _latest_version(db, secret)

    # Apply metadata changes
    if payload.name is not None:
        secret.name = payload.name.strip()
    if payload.description is not None:
        secret.description = payload.description
    if payload.category_id is not None:
        cat = db.get(Category, payload.category_id)
        if cat is None or str(cat.created_by) != str(user.id):
            raise SecretError("Category not found or does not belong to you.")
        secret.category_id = payload.category_id

    db.add(secret)

    # Always generate a new DEK for the new version
    dek, raw_dek = generate_dek(db, settings)

    if payload.value is not None:
        # New plaintext provided — encrypt it
        ciphertext, nonce, auth_tag = _encrypt_value(payload.value, raw_dek)
    else:
        # No new value — decrypt old version and re-encrypt under new DEK
        old_dek = db.get(DataEncryptionKey, sv.dek_id)
        if old_dek is None:
            raise SecretError(f"DEK {sv.dek_id} not found.")
        old_raw_dek = decrypt_dek(old_dek, db, settings)
        plaintext = _decrypt_value(sv.ciphertext, sv.nonce, sv.auth_tag, old_raw_dek)
        ciphertext, nonce, auth_tag = _encrypt_value(plaintext, raw_dek)

    new_tags = payload.tags if payload.tags is not None else sv.metadata_json.get("tags", [])
    new_notes = payload.notes if payload.notes is not None else sv.notes

    new_version = SecretVersion(
        secret_id=secret.id,
        version=sv.version + 1,
        ciphertext=ciphertext,
        nonce=nonce,
        auth_tag=auth_tag,
        dek_id=dek.id,
        notes=new_notes,
        metadata_json={"tags": new_tags},
    )
    db.add(new_version)
    db.commit()
    db.refresh(secret)

    logger.info(
        "Secret updated: id=%s version=%d user=%s",
        secret.id,
        new_version.version,
        user.id,
    )
    return secret


def delete_secret(db: Session, secret_id: UUID, user: User) -> None:
    """Soft-delete a secret by setting deleted_at timestamp.

    Versions are preserved in the database for audit purposes.
    Hard deletion is an admin-only future operation.
    """
    secret = _get_active_secret(db, secret_id, user.id)
    secret.deleted_at = datetime.now(UTC)
    db.add(secret)
    db.commit()
    logger.info("Secret soft-deleted: id=%s user=%s", secret_id, user.id)


def list_secrets(
    db: Session,
    user: User,
    search: str | None = None,
    category_id: UUID | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    """List non-deleted secrets for the current user.

    Supports:
      - Full-text search on name and description (case-insensitive)
      - Filtering by category
      - Pagination
    """
    query = (
        select(Secret)
        .where(Secret.created_by == user.id, Secret.deleted_at.is_(None))
    )

    if search:
        term = f"%{search.lower()}%"
        query = query.where(
            or_(
                func.lower(Secret.name).like(term),
                func.lower(Secret.description).like(term),
            )
        )

    if category_id is not None:
        query = query.where(Secret.category_id == category_id)

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    offset = (page - 1) * page_size
    secrets = list(db.scalars(query.order_by(Secret.created_at.desc()).offset(offset).limit(page_size)))

    # Build summary dicts (attach current version metadata)
    items = []
    for s in secrets:
        sv = db.scalar(
            select(SecretVersion)
            .where(SecretVersion.secret_id == s.id)
            .order_by(SecretVersion.version.desc())
            .limit(1)
        )
        items.append({
            "id": s.id,
            "name": s.name,
            "description": s.description,
            "category_id": s.category_id,
            "created_by": s.created_by,
            "current_version": sv.version if sv else 0,
            "tags": sv.metadata_json.get("tags", []) if sv else [],
            "created_at": s.created_at,
            "updated_at": s.updated_at,
        })

    return {"items": items, "total": total, "page": page, "page_size": page_size}


def list_secret_versions(db: Session, secret_id: UUID, user: User) -> list[dict]:
    """Return all versions of a secret (metadata only — no decrypted values)."""
    secret = _get_active_secret(db, secret_id, user.id)
    versions = list(
        db.scalars(
            select(SecretVersion)
            .where(SecretVersion.secret_id == secret.id)
            .order_by(SecretVersion.version.desc())
        )
    )
    return [
        {
            "id": v.id,
            "version": v.version,
            "notes": v.notes,
            "tags": v.metadata_json.get("tags", []),
            "created_at": v.created_at,
        }
        for v in versions
    ]
