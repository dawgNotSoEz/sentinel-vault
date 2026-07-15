from sqlalchemy.orm import configure_mappers

from app.db.base import Base
from app import models


def test_all_expected_tables_are_registered() -> None:
    expected_tables = {
        "audit_logs",
        "categories",
        "deks",
        "keks",
        "permissions",
        "refresh_tokens",
        "role_permissions",
        "roles",
        "secret_versions",
        "secrets",
        "users",
    }

    assert expected_tables.issubset(set(Base.metadata.tables))


def test_model_relationships_can_be_configured() -> None:
    configure_mappers()

    assert models.User.__tablename__ == "users"
    assert models.Secret.__tablename__ == "secrets"
    assert models.AuditLog.__tablename__ == "audit_logs"


def test_important_indexes_exist() -> None:
    users = Base.metadata.tables["users"]
    secret_versions = Base.metadata.tables["secret_versions"]
    audit_logs = Base.metadata.tables["audit_logs"]

    user_indexes = {index.name for index in users.indexes}
    secret_version_constraints = {constraint.name for constraint in secret_versions.constraints}
    audit_indexes = {index.name for index in audit_logs.indexes}

    assert "ix_users_email" in user_indexes
    assert "uq_secret_versions_secret_id_version" in secret_version_constraints
    assert "ix_audit_logs_user_id_created_at" in audit_indexes
    assert "ix_audit_logs_action_created_at" in audit_indexes
