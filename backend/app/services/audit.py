"""Audit Logging Service — immutable event trail.

Every security-relevant action in Sentinel Vault produces an AuditLog row.
The log is append-only by design: rows are never updated or deleted.

Tracked events:
  - auth.login, auth.logout, auth.register, auth.login_failed, auth.refresh
  - secret.read_value, secret.create, secret.update, secret.delete
  - key.kek_rotated, key.kek_bootstrapped, key.dek_generated
  - permission.denied

Design decisions:
  - Audit logs are written in a SEPARATE db.commit() after the main operation.
    This means a failed audit write does NOT roll back the primary action.
    In production you'd use an outbox pattern or a dedicated audit store —
    but for v1 this is the right pragmatic trade-off.
  - IP and user-agent are passed from the HTTP request layer.
  - resource_id is stored as a UUID string so it works across all resource types.
  - metadata_json stores any extra context (e.g., secret name, version number).
"""

from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog, AuditOutcome
from app.models.user import User

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Event name constants — use these everywhere, no magic strings
# ---------------------------------------------------------------------------

# Auth events
EVENT_AUTH_REGISTER = "auth.register"
EVENT_AUTH_LOGIN = "auth.login"
EVENT_AUTH_LOGIN_FAILED = "auth.login_failed"
EVENT_AUTH_LOGOUT = "auth.logout"
EVENT_AUTH_REFRESH = "auth.refresh"

# Secret events
EVENT_SECRET_CREATE = "secret.create"
EVENT_SECRET_READ_VALUE = "secret.read_value"
EVENT_SECRET_UPDATE = "secret.update"
EVENT_SECRET_DELETE = "secret.delete"

# Key management events
EVENT_KEY_KEK_BOOTSTRAPPED = "key.kek_bootstrapped"
EVENT_KEY_KEK_ROTATED = "key.kek_rotated"
EVENT_KEY_DEK_GENERATED = "key.dek_generated"

# RBAC events
EVENT_PERMISSION_DENIED = "permission.denied"


# ---------------------------------------------------------------------------
# Core log writer
# ---------------------------------------------------------------------------


def log_event(
    db: Session,
    *,
    action: str,
    outcome: AuditOutcome,
    resource_type: str,
    user_id: UUID | None = None,
    resource_id: UUID | str | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
    metadata: dict | None = None,
) -> AuditLog:
    """Persist a single immutable audit log entry.

    This function commits immediately so the log entry is durable even if
    the caller's transaction is later rolled back.

    Args:
        db: Active SQLAlchemy session.
        action: Event name constant (e.g. EVENT_SECRET_READ_VALUE).
        outcome: success, failure, or denied.
        resource_type: e.g. "secret", "kek", "user".
        user_id: Actor's UUID (None for unauthenticated events like failed logins).
        resource_id: Affected resource UUID or string identifier.
        ip_address: Client IP (IPv4 or IPv6).
        user_agent: HTTP User-Agent header.
        metadata: Arbitrary extra context (stored as JSONB).

    Returns:
        The persisted AuditLog row.
    """
    entry = AuditLog(
        user_id=user_id,
        action=action,
        outcome=outcome,
        resource_type=resource_type,
        resource_id=str(resource_id) if resource_id is not None else None,
        ip_address=ip_address,
        user_agent=user_agent,
        metadata_json=metadata or {},
    )
    db.add(entry)
    try:
        db.commit()
        db.refresh(entry)
    except Exception:
        db.rollback()
        logger.exception("Failed to write audit log entry for action=%s", action)
        # Do NOT re-raise — a failed audit write must not break the main flow.

    logger.debug(
        "AUDIT %s action=%s resource=%s/%s outcome=%s",
        user_id,
        action,
        resource_type,
        resource_id,
        outcome,
    )
    return entry


# ---------------------------------------------------------------------------
# Convenience wrappers — one per major event type
# ---------------------------------------------------------------------------


def log_auth_register(
    db: Session,
    user_id: UUID,
    ip: str | None = None,
    ua: str | None = None,
) -> None:
    log_event(
        db,
        action=EVENT_AUTH_REGISTER,
        outcome=AuditOutcome.SUCCESS,
        resource_type="user",
        user_id=user_id,
        resource_id=user_id,
        ip_address=ip,
        user_agent=ua,
    )


def log_auth_login(
    db: Session,
    user_id: UUID,
    ip: str | None = None,
    ua: str | None = None,
) -> None:
    log_event(
        db,
        action=EVENT_AUTH_LOGIN,
        outcome=AuditOutcome.SUCCESS,
        resource_type="user",
        user_id=user_id,
        resource_id=user_id,
        ip_address=ip,
        user_agent=ua,
    )


def log_auth_login_failed(
    db: Session,
    email: str,
    ip: str | None = None,
    ua: str | None = None,
) -> None:
    log_event(
        db,
        action=EVENT_AUTH_LOGIN_FAILED,
        outcome=AuditOutcome.FAILURE,
        resource_type="user",
        user_id=None,
        resource_id=None,
        ip_address=ip,
        user_agent=ua,
        metadata={"attempted_email": email},
    )


def log_auth_logout(
    db: Session,
    user_id: UUID,
    ip: str | None = None,
    ua: str | None = None,
) -> None:
    log_event(
        db,
        action=EVENT_AUTH_LOGOUT,
        outcome=AuditOutcome.SUCCESS,
        resource_type="user",
        user_id=user_id,
        resource_id=user_id,
        ip_address=ip,
        user_agent=ua,
    )


def log_secret_read(
    db: Session,
    user_id: UUID,
    secret_id: UUID,
    secret_name: str,
    ip: str | None = None,
    ua: str | None = None,
) -> None:
    log_event(
        db,
        action=EVENT_SECRET_READ_VALUE,
        outcome=AuditOutcome.SUCCESS,
        resource_type="secret",
        user_id=user_id,
        resource_id=secret_id,
        ip_address=ip,
        user_agent=ua,
        metadata={"secret_name": secret_name},
    )


def log_secret_create(
    db: Session,
    user_id: UUID,
    secret_id: UUID,
    secret_name: str,
    ip: str | None = None,
    ua: str | None = None,
) -> None:
    log_event(
        db,
        action=EVENT_SECRET_CREATE,
        outcome=AuditOutcome.SUCCESS,
        resource_type="secret",
        user_id=user_id,
        resource_id=secret_id,
        ip_address=ip,
        user_agent=ua,
        metadata={"secret_name": secret_name},
    )


def log_secret_update(
    db: Session,
    user_id: UUID,
    secret_id: UUID,
    secret_name: str,
    new_version: int,
    ip: str | None = None,
    ua: str | None = None,
) -> None:
    log_event(
        db,
        action=EVENT_SECRET_UPDATE,
        outcome=AuditOutcome.SUCCESS,
        resource_type="secret",
        user_id=user_id,
        resource_id=secret_id,
        ip_address=ip,
        user_agent=ua,
        metadata={"secret_name": secret_name, "new_version": new_version},
    )


def log_secret_delete(
    db: Session,
    user_id: UUID,
    secret_id: UUID,
    secret_name: str,
    ip: str | None = None,
    ua: str | None = None,
) -> None:
    log_event(
        db,
        action=EVENT_SECRET_DELETE,
        outcome=AuditOutcome.SUCCESS,
        resource_type="secret",
        user_id=user_id,
        resource_id=secret_id,
        ip_address=ip,
        user_agent=ua,
        metadata={"secret_name": secret_name},
    )


def log_kek_rotated(
    db: Session,
    user_id: UUID,
    new_version: int,
    deks_re_encrypted: int,
    ip: str | None = None,
    ua: str | None = None,
) -> None:
    log_event(
        db,
        action=EVENT_KEY_KEK_ROTATED,
        outcome=AuditOutcome.SUCCESS,
        resource_type="kek",
        user_id=user_id,
        ip_address=ip,
        user_agent=ua,
        metadata={"new_version": new_version, "deks_re_encrypted": deks_re_encrypted},
    )


def log_permission_denied(
    db: Session,
    user_id: UUID | None,
    action: str,
    resource_type: str,
    resource_id: UUID | str | None = None,
    ip: str | None = None,
    ua: str | None = None,
) -> None:
    log_event(
        db,
        action=EVENT_PERMISSION_DENIED,
        outcome=AuditOutcome.DENIED,
        resource_type=resource_type,
        user_id=user_id,
        resource_id=resource_id,
        ip_address=ip,
        user_agent=ua,
        metadata={"attempted_action": action},
    )


# ---------------------------------------------------------------------------
# Audit query helpers (for the audit dashboard API)
# ---------------------------------------------------------------------------


def get_audit_logs(
    db: Session,
    user_id: UUID | None = None,
    action: str | None = None,
    resource_type: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> dict:
    """Query audit logs with optional filters. Returns paginated results."""
    from sqlalchemy import func

    query = select(AuditLog).order_by(AuditLog.created_at.desc())

    if user_id is not None:
        query = query.where(AuditLog.user_id == user_id)
    if action is not None:
        query = query.where(AuditLog.action == action)
    if resource_type is not None:
        query = query.where(AuditLog.resource_type == resource_type)

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    offset = (page - 1) * page_size
    rows = list(db.scalars(query.offset(offset).limit(page_size)))

    return {
        "items": rows,
        "total": total,
        "page": page,
        "page_size": page_size,
    }
