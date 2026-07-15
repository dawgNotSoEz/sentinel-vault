"""RBAC API Routes.

Prefix: /api/v1/roles
Tags:   rbac

Endpoints:
  GET  /roles                       — list all roles with permissions (admin)
  GET  /roles/{role_name}           — single role detail (admin)
  GET  /roles/me                    — current user's role + permissions
  POST /roles/seed                  — seed built-in roles (admin, first-run)
  GET  /users                       — list all users (admin)
  POST /users/{user_id}/role        — assign role to user (admin)
  POST /users/{user_id}/deactivate  — deactivate user (admin)
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.rbac import DeactivateResponse, PermissionResponse, RoleResponse, UserAdminView, UserRoleAssign
from app.services.rbac import (
    PERM_ROLES_READ,
    PERM_USERS_ASSIGN_ROLE,
    PERM_USERS_DEACTIVATE,
    PERM_USERS_READ,
    assign_role_to_user,
    deactivate_user,
    get_role_by_name,
    get_user_permissions,
    is_admin,
    list_roles,
    list_users,
    require_admin,
    require_permission,
    seed_roles_and_permissions,
)

router = APIRouter(prefix="/roles", tags=["rbac"])


# ---------------------------------------------------------------------------
# Current user's own role
# ---------------------------------------------------------------------------


@router.get(
    "/me",
    summary="Get your own role and permissions",
    description="Returns the currently authenticated user's role name and list of permissions.",
)
def my_role(current_user: User = Depends(get_current_user)) -> dict:
    return {
        "role": current_user.role.name if current_user.role else None,
        "permissions": sorted(get_user_permissions(current_user)),
    }


# ---------------------------------------------------------------------------
# Role management (admin only)
# ---------------------------------------------------------------------------


@router.post(
    "/seed",
    status_code=status.HTTP_201_CREATED,
    summary="Seed built-in roles and permissions",
    description=(
        "Creates admin, developer, and viewer roles with their default permissions. "
        "Idempotent — safe to call multiple times. Admin only."
    ),
)
def seed_roles(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin()),
) -> dict:
    seed_roles_and_permissions(db)
    roles = list_roles(db)
    return {
        "message": "Roles seeded successfully.",
        "roles": [r.name for r in roles],
    }


@router.get(
    "",
    response_model=list[RoleResponse],
    summary="List all roles with permissions",
)
def list_all_roles(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(PERM_ROLES_READ)),
) -> list[RoleResponse]:
    roles = list_roles(db)
    return [RoleResponse.model_validate(r) for r in roles]


@router.get(
    "/{role_name}",
    response_model=RoleResponse,
    summary="Get a single role by name",
)
def get_role(
    role_name: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(PERM_ROLES_READ)),
) -> RoleResponse:
    role = get_role_by_name(db, role_name)
    if role is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Role '{role_name}' not found.")
    return RoleResponse.model_validate(role)


# ---------------------------------------------------------------------------
# User management (admin only)
# ---------------------------------------------------------------------------


@router.get(
    "/users/all",
    response_model=list[UserAdminView],
    summary="List all users (admin)",
    description="Returns all registered users with their role assignments.",
)
def list_all_users(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(PERM_USERS_READ)),
) -> list[UserAdminView]:
    users = list_users(db)
    return [UserAdminView.from_user(u) for u in users]


@router.post(
    "/users/{user_id}/role",
    response_model=UserAdminView,
    summary="Assign a role to a user",
    description="Admin-only. Overwrites the user's existing role.",
)
def assign_role(
    user_id: UUID,
    payload: UserRoleAssign,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission(PERM_USERS_ASSIGN_ROLE)),
) -> UserAdminView:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User {user_id} not found.")
    try:
        updated = assign_role_to_user(db, user, payload.role_name)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return UserAdminView.from_user(updated)


@router.post(
    "/users/{user_id}/deactivate",
    response_model=DeactivateResponse,
    summary="Deactivate a user account",
    description="Admin-only. Deactivated users cannot log in. Irreversible via API (DB reset required).",
)
def deactivate(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission(PERM_USERS_DEACTIVATE)),
) -> DeactivateResponse:
    try:
        deactivate_user(db, user_id, current_user)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return DeactivateResponse(message="User deactivated.", user_id=user_id)
