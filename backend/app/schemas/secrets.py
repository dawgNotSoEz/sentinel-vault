"""Pydantic schemas for Secret Management.

Design rules:
  - Plaintext `value` only appears in create/update requests and the
    explicit `GET /secrets/{id}/value` response — never in list responses.
  - Tags are stored as a list of strings inside SecretVersion.metadata_json.
  - All UUIDs are serialised as strings in responses for JSON compatibility.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Category schemas
# ---------------------------------------------------------------------------


class CategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    description: str = Field(default="", max_length=255)


class CategoryResponse(BaseModel):
    id: UUID
    name: str
    description: str
    created_by: UUID
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Secret CRUD schemas
# ---------------------------------------------------------------------------


class SecretCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=500)
    value: str = Field(min_length=1, description="Plaintext secret value — encrypted at rest.")
    category_id: UUID | None = None
    tags: list[str] = Field(default_factory=list)
    notes: str = Field(default="", max_length=1000)


class SecretUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=500)
    value: str | None = Field(default=None, min_length=1)
    category_id: UUID | None = None
    tags: list[str] | None = None
    notes: str | None = None


class SecretVersionResponse(BaseModel):
    """Metadata for a single version — never includes decrypted value."""

    id: UUID
    version: int
    notes: str
    tags: list[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class SecretSummary(BaseModel):
    """List-safe view — no plaintext value."""

    id: UUID
    name: str
    description: str
    category_id: UUID | None
    created_by: UUID
    current_version: int
    tags: list[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SecretValueResponse(BaseModel):
    """Returned only from GET /secrets/{id}/value — contains decrypted value."""

    id: UUID
    name: str
    value: str
    version: int
    tags: list[str]
    notes: str
    retrieved_at: datetime


class SecretListResponse(BaseModel):
    items: list[SecretSummary]
    total: int
    page: int
    page_size: int
