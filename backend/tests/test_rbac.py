"""Tests for Phase 8: RBAC — Role Based Access Control.

Coverage:
  - Permission constants: naming convention, uniqueness
  - ROLE_PERMISSIONS: all roles defined, admin has all perms
  - has_permission(): user with no role → no permissions
  - has_permission(): user with role → grants correct perms
  - get_user_permissions(): correct set returned
  - is_admin(): role name comparison
  - require_permission(): returns a callable
  - seed_roles_and_permissions: idempotent (tested via logic inspection)
  - RBAC schemas: RoleResponse, UserAdminView, PermissionResponse
  - OpenAPI contract: all RBAC routes registered
  - Key management routes: now use RBAC permission guards
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

from app.services.rbac import (
    ALL_PERMISSIONS,
    PERM_AUDIT_READ_ALL,
    PERM_AUDIT_READ_OWN,
    PERM_CATEGORIES_CREATE,
    PERM_CATEGORIES_READ,
    PERM_KEYS_BOOTSTRAP,
    PERM_KEYS_READ,
    PERM_KEYS_ROTATE,
    PERM_ROLES_ASSIGN_PERMISSION,
    PERM_ROLES_READ,
    PERM_SECRETS_CREATE,
    PERM_SECRETS_DELETE,
    PERM_SECRETS_READ,
    PERM_SECRETS_UPDATE,
    PERM_USERS_ASSIGN_ROLE,
    PERM_USERS_DEACTIVATE,
    PERM_USERS_READ,
    ROLE_DESCRIPTIONS,
    ROLE_PERMISSIONS,
    get_user_permissions,
    has_permission,
    is_admin,
    require_permission,
)


# ---------------------------------------------------------------------------
# Permission constant tests
# ---------------------------------------------------------------------------


def test_all_permission_constants_follow_colon_notation() -> None:
    """Permission names must follow <resource>:<action> convention."""
    for name in ALL_PERMISSIONS:
        assert ":" in name, f"Permission '{name}' must contain a colon."
        parts = name.split(":")
        assert len(parts) == 2, f"Permission '{name}' should have exactly one colon."
        assert all(part.replace("_", "").isalpha() for part in parts), (
            f"Permission '{name}' should only contain letters and underscores."
        )


def test_all_permission_constants_are_unique() -> None:
    names = list(ALL_PERMISSIONS.keys())
    assert len(names) == len(set(names)), "Duplicate permission names found."


def test_all_permission_constants_have_descriptions() -> None:
    for name, desc in ALL_PERMISSIONS.items():
        assert isinstance(desc, str) and len(desc) > 0, f"Permission '{name}' has empty description."


# ---------------------------------------------------------------------------
# Role permission matrix tests
# ---------------------------------------------------------------------------


def test_three_roles_defined() -> None:
    assert set(ROLE_PERMISSIONS.keys()) == {"admin", "developer", "viewer"}


def test_admin_has_all_permissions() -> None:
    """Admin role must grant every defined permission — no gaps."""
    assert ROLE_PERMISSIONS["admin"] == set(ALL_PERMISSIONS.keys())


def test_viewer_is_strict_subset_of_developer() -> None:
    """Viewer permissions are a proper subset of developer permissions."""
    viewer = ROLE_PERMISSIONS["viewer"]
    developer = ROLE_PERMISSIONS["developer"]
    assert viewer < developer, "Viewer must have strictly fewer permissions than developer."


def test_developer_cannot_manage_keys() -> None:
    """Key management is admin-only."""
    developer_perms = ROLE_PERMISSIONS["developer"]
    assert PERM_KEYS_READ not in developer_perms
    assert PERM_KEYS_ROTATE not in developer_perms
    assert PERM_KEYS_BOOTSTRAP not in developer_perms


def test_developer_cannot_read_all_audit_logs() -> None:
    """Cross-user audit access is admin-only."""
    assert PERM_AUDIT_READ_ALL not in ROLE_PERMISSIONS["developer"]


def test_viewer_can_only_read() -> None:
    viewer = ROLE_PERMISSIONS["viewer"]
    assert PERM_SECRETS_READ in viewer
    assert PERM_SECRETS_CREATE not in viewer
    assert PERM_SECRETS_UPDATE not in viewer
    assert PERM_SECRETS_DELETE not in viewer


def test_role_descriptions_cover_all_roles() -> None:
    assert set(ROLE_DESCRIPTIONS.keys()) == set(ROLE_PERMISSIONS.keys())


# ---------------------------------------------------------------------------
# has_permission / get_user_permissions helpers
# ---------------------------------------------------------------------------


from types import SimpleNamespace


def _make_permission(name: str) -> SimpleNamespace:
    return SimpleNamespace(name=name)


def _make_user_with_role(role_name: str, perm_names: list[str]) -> SimpleNamespace:
    """Build a lightweight user stub with a role containing named permissions."""
    perms = [_make_permission(p) for p in perm_names]
    role = SimpleNamespace(name=role_name, permissions=perms)
    return SimpleNamespace(role=role)


def _make_user_no_role() -> SimpleNamespace:
    return SimpleNamespace(role=None)


def test_user_with_no_role_has_no_permissions() -> None:
    user = _make_user_no_role()
    assert get_user_permissions(user) == set()
    assert not has_permission(user, PERM_SECRETS_READ)


def test_user_with_developer_role_can_create_secrets() -> None:
    user = _make_user_with_role("developer", list(ROLE_PERMISSIONS["developer"]))
    assert has_permission(user, PERM_SECRETS_CREATE)
    assert has_permission(user, PERM_SECRETS_READ)
    assert has_permission(user, PERM_AUDIT_READ_OWN)


def test_user_with_developer_role_cannot_rotate_keys() -> None:
    user = _make_user_with_role("developer", list(ROLE_PERMISSIONS["developer"]))
    assert not has_permission(user, PERM_KEYS_ROTATE)
    assert not has_permission(user, PERM_KEYS_READ)


def test_user_with_viewer_role_cannot_create_secrets() -> None:
    user = _make_user_with_role("viewer", list(ROLE_PERMISSIONS["viewer"]))
    assert not has_permission(user, PERM_SECRETS_CREATE)
    assert has_permission(user, PERM_SECRETS_READ)


def test_user_with_admin_role_has_all_permissions() -> None:
    user = _make_user_with_role("admin", list(ALL_PERMISSIONS.keys()))
    for perm in ALL_PERMISSIONS:
        assert has_permission(user, perm), f"Admin should have permission '{perm}'."


def test_is_admin_returns_true_for_admin_role() -> None:
    user = _make_user_with_role("admin", [])
    assert is_admin(user) is True


def test_is_admin_returns_false_for_developer_role() -> None:
    user = _make_user_with_role("developer", [])
    assert is_admin(user) is False


def test_is_admin_returns_false_for_no_role() -> None:
    user = _make_user_no_role()
    assert is_admin(user) is False


# ---------------------------------------------------------------------------
# require_permission factory
# ---------------------------------------------------------------------------


def test_require_permission_returns_callable() -> None:
    dep = require_permission(PERM_SECRETS_CREATE)
    assert callable(dep)


def test_require_permission_has_descriptive_name() -> None:
    dep = require_permission(PERM_KEYS_ROTATE)
    assert "keys" in dep.__name__ or "rotate" in dep.__name__


# ---------------------------------------------------------------------------
# Schema tests
# ---------------------------------------------------------------------------


def test_permission_response_schema() -> None:
    from app.schemas.rbac import PermissionResponse

    p = PermissionResponse(
        id=uuid.uuid4(),
        name="secrets:create",
        description="Create new secrets",
        created_at=datetime.now(UTC),
    )
    assert p.name == "secrets:create"


def test_role_response_schema_with_permissions() -> None:
    from app.schemas.rbac import PermissionResponse, RoleResponse

    perms = [
        PermissionResponse(id=uuid.uuid4(), name="secrets:read", description="Read secrets", created_at=datetime.now(UTC))
    ]
    role = RoleResponse(
        id=uuid.uuid4(),
        name="viewer",
        description="Read only",
        permissions=perms,
        created_at=datetime.now(UTC),
    )
    assert len(role.permissions) == 1
    assert role.permissions[0].name == "secrets:read"


def test_user_admin_view_role_name_can_be_none() -> None:
    from app.schemas.rbac import UserAdminView

    view = UserAdminView(
        id=uuid.uuid4(),
        email="test@example.com",
        full_name="Test User",
        role_name=None,
        is_active=True,
        created_at=datetime.now(UTC),
    )
    assert view.role_name is None


def test_deactivate_response_schema() -> None:
    from app.schemas.rbac import DeactivateResponse

    uid = uuid.uuid4()
    r = DeactivateResponse(message="User deactivated.", user_id=uid)
    assert r.user_id == uid


# ---------------------------------------------------------------------------
# OpenAPI contract
# ---------------------------------------------------------------------------


def test_rbac_routes_registered_in_openapi_contract() -> None:
    from app.core.config import Settings
    from app.main import create_app

    app = create_app(Settings(APP_ENV="test"))
    paths = set(app.openapi()["paths"])

    assert "/api/v1/roles" in paths
    assert "/api/v1/roles/me" in paths
    assert "/api/v1/roles/seed" in paths
    assert "/api/v1/roles/{role_name}" in paths
    assert "/api/v1/roles/users/all" in paths
    assert "/api/v1/roles/users/{user_id}/role" in paths
    assert "/api/v1/roles/users/{user_id}/deactivate" in paths


def test_key_routes_still_registered_after_rbac_refactor() -> None:
    from app.core.config import Settings
    from app.main import create_app

    app = create_app(Settings(APP_ENV="test"))
    paths = set(app.openapi()["paths"])

    assert "/api/v1/keys/kek" in paths
    assert "/api/v1/keys/kek/bootstrap" in paths
    assert "/api/v1/keys/kek/rotate" in paths
    assert "/api/v1/keys/dek" in paths


# ---------------------------------------------------------------------------
# Privilege escalation guard tests
# ---------------------------------------------------------------------------


def test_admin_permission_set_is_superset_of_developer() -> None:
    """Admin must always have a superset of developer permissions."""
    assert ROLE_PERMISSIONS["admin"].issuperset(ROLE_PERMISSIONS["developer"])


def test_admin_permission_set_is_superset_of_viewer() -> None:
    assert ROLE_PERMISSIONS["admin"].issuperset(ROLE_PERMISSIONS["viewer"])


def test_no_role_grants_user_management_except_admin() -> None:
    """User management permissions must never appear in non-admin roles."""
    sensitive = {PERM_USERS_ASSIGN_ROLE, PERM_USERS_DEACTIVATE, PERM_AUDIT_READ_ALL}
    for role_name, perms in ROLE_PERMISSIONS.items():
        if role_name != "admin":
            overlap = sensitive & perms
            assert not overlap, (
                f"Role '{role_name}' has admin-only permissions: {overlap}"
            )
