"""RBAC Service — Role-Based Access Control.

Three built-in roles with granular permissions:

  ┌─────────────┬──────────────────────────────────────────────────────┐
  │ Role        │ Permissions                                          │
  ├─────────────┼──────────────────────────────────────────────────────┤
  │ admin       │ ALL permissions                                      │
  │ developer   │ secrets:*, categories:*, audit:read_own             │
  │ viewer      │ secrets:read, categories:read, audit:read_own       │
  └─────────────┴──────────────────────────────────────────────────────┘

Design:
  - Permission names follow <resource>:<action> convention.
  - seed_roles_and_permissions() is idempotent — safe to call on every startup.
  - require_permission() returns a FastAPI Depends()-compatible callable.
  - Users without a role have ZERO permissions (fail-secure default).
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from uuid import UUID

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.role import Permission, Role
from app.models.user import User

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Permission name constants
# ---------------------------------------------------------------------------

# Secrets
PERM_SECRETS_CREATE = "secrets:create"
PERM_SECRETS_READ = "secrets:read"
PERM_SECRETS_UPDATE = "secrets:update"
PERM_SECRETS_DELETE = "secrets:delete"

# Categories
PERM_CATEGORIES_CREATE = "categories:create"
PERM_CATEGORIES_READ = "categories:read"

# Audit
PERM_AUDIT_READ_OWN = "audit:read_own"
PERM_AUDIT_READ_ALL = "audit:read_all"

# Key management
PERM_KEYS_READ = "keys:read"
PERM_KEYS_ROTATE = "keys:rotate"
PERM_KEYS_BOOTSTRAP = "keys:bootstrap"

# User management
PERM_USERS_READ = "users:read"
PERM_USERS_ASSIGN_ROLE = "users:assign_role"
PERM_USERS_DEACTIVATE = "users:deactivate"

# Role management
PERM_ROLES_READ = "roles:read"
PERM_ROLES_ASSIGN_PERMISSION = "roles:assign_permission"

ALL_PERMISSIONS: dict[str, str] = {
    PERM_SECRETS_CREATE: "Create new secrets",
    PERM_SECRETS_READ: "Read secret metadata and values",
    PERM_SECRETS_UPDATE: "Update existing secrets (creates new version)",
    PERM_SECRETS_DELETE: "Soft-delete secrets",
    PERM_CATEGORIES_CREATE: "Create secret categories",
    PERM_CATEGORIES_READ: "List secret categories",
    PERM_AUDIT_READ_OWN: "Read own audit trail",
    PERM_AUDIT_READ_ALL: "Read all users' audit logs (admin only)",
    PERM_KEYS_READ: "Read KEK/DEK metadata",
    PERM_KEYS_ROTATE: "Rotate the active KEK",
    PERM_KEYS_BOOTSTRAP: "Bootstrap the initial KEK",
    PERM_USERS_READ: "List and view users",
    PERM_USERS_ASSIGN_ROLE: "Assign roles to users",
    PERM_USERS_DEACTIVATE: "Deactivate user accounts",
    PERM_ROLES_READ: "List roles and their permissions",
    PERM_ROLES_ASSIGN_PERMISSION: "Assign permissions to roles",
}

# Role → set of permission names
ROLE_PERMISSIONS: dict[str, set[str]] = {
    "admin": set(ALL_PERMISSIONS.keys()),  # admin gets everything
    "developer": {
        PERM_SECRETS_CREATE,
        PERM_SECRETS_READ,
        PERM_SECRETS_UPDATE,
        PERM_SECRETS_DELETE,
        PERM_CATEGORIES_CREATE,
        PERM_CATEGORIES_READ,
        PERM_AUDIT_READ_OWN,
    },
    "viewer": {
        PERM_SECRETS_READ,
        PERM_CATEGORIES_READ,
        PERM_AUDIT_READ_OWN,
    },
}

ROLE_DESCRIPTIONS: dict[str, str] = {
    "admin": "Full access to all resources and operations.",
    "developer": "Can create, read, update, and delete own secrets. Read-only audit access.",
    "viewer": "Read-only access to secrets and categories.",
}


# ---------------------------------------------------------------------------
# Permission check helpers
# ---------------------------------------------------------------------------


def get_user_permissions(user: User) -> set[str]:
    """Return the set of permission names granted to the user via their role.

    Users with no role get ZERO permissions (fail-secure).
    """
    if user.role is None:
        return set()
    return {p.name for p in user.role.permissions}


def has_permission(user: User, permission: str) -> bool:
    """Return True if the user has the given permission."""
    return permission in get_user_permissions(user)


def is_admin(user: User) -> bool:
    """Shorthand: check if the user has the admin role."""
    return user.role is not None and user.role.name == "admin"


# ---------------------------------------------------------------------------
# FastAPI dependency factory
# ---------------------------------------------------------------------------


def require_permission(permission: str) -> Callable:
    """Return a FastAPI dependency that enforces a specific permission.

    Usage:
        @router.get("/endpoint")
        def endpoint(user: User = Depends(require_permission(PERM_SECRETS_CREATE))):
            ...

    Raises HTTP 403 if the user lacks the required permission.
    """
    from app.api.deps import get_current_user

    def _check(current_user: User = Depends(get_current_user)) -> User:
        if not has_permission(current_user, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission '{permission}' required.",
            )
        return current_user

    # Give the dependency a descriptive name for OpenAPI docs
    _check.__name__ = f"require_{permission.replace(':', '_')}"
    return _check


def require_admin() -> Callable:
    """Convenience: require the admin role (has all permissions)."""
    from app.api.deps import get_current_user

    def _check(current_user: User = Depends(get_current_user)) -> User:
        if not is_admin(current_user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin role required.",
            )
        return current_user

    _check.__name__ = "require_admin_role"
    return _check


# ---------------------------------------------------------------------------
# Role & Permission seeder
# ---------------------------------------------------------------------------


def seed_roles_and_permissions(db: Session) -> None:
    """Create the three built-in roles and all permissions if they don't exist.

    This function is idempotent — safe to call on every application startup.
    It uses upsert-style logic: if a role/permission already exists it is
    not modified (existing assignments are preserved).
    """
    # 1. Upsert all permissions
    perm_objects: dict[str, Permission] = {}
    for name, description in ALL_PERMISSIONS.items():
        existing = db.scalar(select(Permission).where(Permission.name == name))
        if existing is None:
            perm = Permission(name=name, description=description)
            db.add(perm)
            db.flush()
            perm_objects[name] = perm
            logger.info("Created permission: %s", name)
        else:
            perm_objects[name] = existing

    db.commit()

    # 2. Upsert roles and assign their permissions
    for role_name, perm_names in ROLE_PERMISSIONS.items():
        role = db.scalar(select(Role).where(Role.name == role_name))
        if role is None:
            role = Role(name=role_name, description=ROLE_DESCRIPTIONS[role_name])
            db.add(role)
            db.flush()
            logger.info("Created role: %s", role_name)

        # Assign any missing permissions to the role
        existing_perm_names = {p.name for p in role.permissions}
        for perm_name in perm_names:
            if perm_name not in existing_perm_names:
                role.permissions.append(perm_objects[perm_name])

        db.add(role)

    db.commit()
    logger.info("RBAC seed complete.")


# ---------------------------------------------------------------------------
# Runtime management (for the roles API)
# ---------------------------------------------------------------------------


def list_roles(db: Session) -> list[Role]:
    return list(db.scalars(select(Role).order_by(Role.name.asc())))


def get_role_by_name(db: Session, name: str) -> Role | None:
    return db.scalar(select(Role).where(Role.name == name))


def assign_role_to_user(db: Session, user: User, role_name: str) -> User:
    """Assign a named role to a user. Raises ValueError if the role doesn't exist."""
    role = get_role_by_name(db, role_name)
    if role is None:
        raise ValueError(f"Role '{role_name}' not found. Call seed first.")
    user.role_id = role.id
    db.add(user)
    db.commit()
    db.refresh(user)
    logger.info("Assigned role '%s' to user %s", role_name, user.id)
    return user


def list_users(db: Session) -> list[User]:
    return list(db.scalars(select(User).order_by(User.created_at.desc())))


def deactivate_user(db: Session, user_id: UUID, admin_user: User) -> User:
    """Deactivate a user account. Admins cannot deactivate themselves."""
    if str(user_id) == str(admin_user.id):
        raise ValueError("You cannot deactivate your own account.")
    user = db.get(User, user_id)
    if user is None:
        raise ValueError(f"User {user_id} not found.")
    user.is_active = False
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
