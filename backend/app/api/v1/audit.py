"""Audit Log API routes.

Prefix: /api/v1/audit
Tags:   audit

Access control:
  - Admin: can query all logs (any user, any resource)
  - Regular user: can only query their own audit logs

This endpoint powers the audit dashboard in the frontend (Phase 9).
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, settings_provider
from app.db.session import get_db
from app.models.user import User
from app.schemas.audit import AuditListResponse, AuditLogResponse
from app.services.audit import get_audit_logs

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get(
    "",
    response_model=AuditListResponse,
    summary="Query audit logs",
    description=(
        "Admins can filter by any user. Regular users only see their own logs. "
        "Results are ordered by most recent first."
    ),
)
def list_audit_logs(
    action: str | None = Query(default=None, description="Filter by event action (e.g. secret.read_value)"),
    resource_type: str | None = Query(default=None, description="Filter by resource type (secret, user, kek)"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AuditListResponse:
    # Determine user_id filter: admins see all, others see only their own
    is_admin = current_user.role is not None and current_user.role.name == "admin"
    user_id_filter = None if is_admin else current_user.id

    result = get_audit_logs(
        db,
        user_id=user_id_filter,
        action=action,
        resource_type=resource_type,
        page=page,
        page_size=page_size,
    )
    return AuditListResponse(
        items=[AuditLogResponse.model_validate(r) for r in result["items"]],
        total=result["total"],
        page=result["page"],
        page_size=result["page_size"],
    )


@router.get(
    "/me",
    response_model=AuditListResponse,
    summary="Get your own audit trail",
    description="Returns all audit log entries for the currently authenticated user.",
)
def my_audit_logs(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AuditListResponse:
    result = get_audit_logs(db, user_id=current_user.id, page=page, page_size=page_size)
    return AuditListResponse(
        items=[AuditLogResponse.model_validate(r) for r in result["items"]],
        total=result["total"],
        page=result["page"],
        page_size=result["page_size"],
    )
