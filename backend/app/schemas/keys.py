"""Pydantic schemas for the Key Management API.

Sensitive fields (encrypted_key_material) are deliberately excluded from all
response models — the API surface only exposes metadata, never key bytes.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.key import KeyStatus


class KEKResponse(BaseModel):
    """Public metadata for a Key Encryption Key."""

    id: UUID
    version: int
    status: KeyStatus
    provider: str
    rotated_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class DEKResponse(BaseModel):
    """Public metadata for a Data Encryption Key."""

    id: UUID
    kek_id: UUID
    kek_version: int
    created_at: datetime

    model_config = {"from_attributes": True}


class KEKListResponse(BaseModel):
    """Paginated list of KEK metadata."""

    items: list[KEKResponse]
    total: int


class DEKListResponse(BaseModel):
    """Paginated list of DEK metadata."""

    items: list[DEKResponse]
    total: int


class RotateKEKResponse(BaseModel):
    """Response after a successful KEK rotation."""

    new_kek: KEKResponse
    deks_re_encrypted: int = Field(
        description="Number of DEKs re-encrypted under the new KEK."
    )
    message: str = Field(default="KEK rotation completed successfully.")
