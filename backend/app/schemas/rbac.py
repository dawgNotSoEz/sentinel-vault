"""Pydantic schemas for RBAC API."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class PermissionResponse(BaseModel):
    id: UUID
    name: str
    description: str
    created_at: datetime

    model_config = {"from_attributes": True}


class RoleResponse(BaseModel):
    id: UUID
    name: str
    description: str
    permissions: list[PermissionResponse]
    created_at: datetime

    model_config = {"from_attributes": True}


class UserRoleAssign(BaseModel):
    role_name: str


class UserAdminView(BaseModel):
    """User view exposed to admins (no password hash)."""

    id: UUID
    email: str
    full_name: str
    role_name: str | None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}

    @classmethod
    def from_user(cls, user) -> "UserAdminView":
        return cls(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            role_name=user.role.name if user.role else None,
            is_active=user.is_active,
            created_at=user.created_at,
        )


class DeactivateResponse(BaseModel):
    message: str
    user_id: UUID
