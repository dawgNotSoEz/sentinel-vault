"""Pydantic schemas for Audit Log API."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.models.audit_log import AuditOutcome


class AuditLogResponse(BaseModel):
    id: UUID
    user_id: UUID | None
    action: str
    resource_type: str
    resource_id: str | None
    ip_address: str | None
    user_agent: str | None
    outcome: AuditOutcome
    metadata_json: dict
    created_at: datetime

    model_config = {"from_attributes": True}


class AuditListResponse(BaseModel):
    items: list[AuditLogResponse]
    total: int
    page: int
    page_size: int
