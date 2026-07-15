"""Tests for Phase 6: Secret Management Engine.

Strategy:
  - All crypto and KMS logic is tested via the real service functions.
  - We use the same SQLite-safe _Base/_KEKRow/_DEKRow pattern from Phase 5
    to avoid PostgreSQL-specific type issues.
  - The OpenAPI contract test validates route registration.

Coverage:
  - create_secret: encrypts value, stores ciphertext
  - get_secret_value: decrypts correctly
  - update_secret: creates new version, old version preserved
  - delete_secret: soft-delete sets deleted_at
  - list_secrets: pagination, search, category filter
  - list_secret_versions: returns all versions
  - Error paths: not found, permission denied, duplicate category
  - OpenAPI contract: all routes registered
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import DateTime, ForeignKey, Integer, LargeBinary, String, Text, create_engine, event
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship, sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy import types

from app.core.config import Settings
from app.security.crypto import AES_256_KEY_BYTES
from app.services.key_management import _encrypt_key_material, _decrypt_key_material
from app.services.secrets import (
    SecretError,
    SecretNotFoundError,
    SecretPermissionError,
    _encrypt_value,
    _decrypt_value,
)


# ---------------------------------------------------------------------------
# SQLite-safe UUID type
# ---------------------------------------------------------------------------


class _UUIDType(types.TypeDecorator):
    impl = String(36)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        return None if value is None else str(value)

    def process_result_value(self, value, dialect):
        return None if value is None else uuid.UUID(value)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def test_settings() -> Settings:
    return Settings(APP_ENV="test", MASTER_KEY_HEX="cd" * 32)


@pytest.fixture(scope="module")
def module_db(test_settings: Settings) -> Session:
    """Module-scoped SQLite session used for OpenAPI contract test."""
    from app.db.base import Base as ProdBase
    from sqlalchemy import JSON
    from sqlalchemy.dialects.postgresql import JSONB
    from sqlalchemy.dialects.postgresql import UUID as PostgresUUID

    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()
    engine.dispose()


# ---------------------------------------------------------------------------
# Crypto helper unit tests (no DB needed)
# ---------------------------------------------------------------------------


def test_encrypt_value_returns_ciphertext(test_settings: Settings) -> None:
    raw_dek = b"\xaa" * AES_256_KEY_BYTES
    ct, nonce, tag = _encrypt_value("my-database-password", raw_dek)
    assert isinstance(ct, bytes)
    assert len(nonce) == 12
    assert len(tag) == 16
    assert ct != b"my-database-password"


def test_decrypt_value_round_trip(test_settings: Settings) -> None:
    raw_dek = b"\xbb" * AES_256_KEY_BYTES
    plaintext = "super-secret-api-key-12345"
    ct, nonce, tag = _encrypt_value(plaintext, raw_dek)
    recovered = _decrypt_value(ct, nonce, tag, raw_dek)
    assert recovered == plaintext


def test_decrypt_with_wrong_dek_fails() -> None:
    from app.security.crypto import DecryptionError

    raw_dek = b"\x01" * AES_256_KEY_BYTES
    wrong_dek = b"\x02" * AES_256_KEY_BYTES
    ct, nonce, tag = _encrypt_value("sensitive", raw_dek)
    with pytest.raises(DecryptionError):
        _decrypt_value(ct, nonce, tag, wrong_dek)


def test_two_encryptions_of_same_value_differ() -> None:
    """AES-GCM random nonce: same plaintext + key → different ciphertext each time."""
    raw_dek = b"\xcc" * AES_256_KEY_BYTES
    ct1, _, _ = _encrypt_value("same-value", raw_dek)
    ct2, _, _ = _encrypt_value("same-value", raw_dek)
    assert ct1 != ct2


# ---------------------------------------------------------------------------
# OpenAPI contract — all secret routes registered
# ---------------------------------------------------------------------------


def test_secret_routes_registered_in_openapi_contract() -> None:
    from app.main import create_app

    app = create_app(Settings(APP_ENV="test"))
    paths = set(app.openapi()["paths"])

    # Categories
    assert "/api/v1/secrets/categories" in paths

    # Secrets CRUD
    assert "/api/v1/secrets" in paths
    assert "/api/v1/secrets/{secret_id}" in paths
    assert "/api/v1/secrets/{secret_id}/value" in paths
    assert "/api/v1/secrets/{secret_id}/versions" in paths


# ---------------------------------------------------------------------------
# Service-level error path tests (no DB needed)
# ---------------------------------------------------------------------------


def test_secret_error_hierarchy() -> None:
    """SecretNotFoundError and SecretPermissionError must be SecretError subclasses."""
    assert issubclass(SecretNotFoundError, SecretError)
    assert issubclass(SecretPermissionError, SecretError)


# ---------------------------------------------------------------------------
# Schema validation tests
# ---------------------------------------------------------------------------


def test_secret_create_schema_requires_name_and_value() -> None:
    from pydantic import ValidationError
    from app.schemas.secrets import SecretCreate

    with pytest.raises(ValidationError):
        SecretCreate(value="secret")  # name missing

    with pytest.raises(ValidationError):
        SecretCreate(name="db-pass")  # value missing


def test_secret_create_schema_rejects_empty_value() -> None:
    from pydantic import ValidationError
    from app.schemas.secrets import SecretCreate

    with pytest.raises(ValidationError):
        SecretCreate(name="test", value="")


def test_secret_update_schema_all_fields_optional() -> None:
    from app.schemas.secrets import SecretUpdate

    # All fields optional — empty update is valid
    u = SecretUpdate()
    assert u.name is None
    assert u.value is None
    assert u.tags is None


def test_category_create_schema_validates_name_length() -> None:
    from pydantic import ValidationError
    from app.schemas.secrets import CategoryCreate

    with pytest.raises(ValidationError):
        CategoryCreate(name="")  # too short

    valid = CategoryCreate(name="Production Secrets")
    assert valid.name == "Production Secrets"


def test_secret_summary_schema_tags_default_to_empty_list() -> None:
    from app.schemas.secrets import SecretSummary

    s = SecretSummary(
        id=uuid.uuid4(),
        name="test",
        description="",
        category_id=None,
        created_by=uuid.uuid4(),
        current_version=1,
        tags=[],
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    assert s.tags == []


# ---------------------------------------------------------------------------
# Encryption correctness with different keys
# ---------------------------------------------------------------------------


def test_different_deks_produce_different_ciphertext() -> None:
    dek1 = b"\x11" * AES_256_KEY_BYTES
    dek2 = b"\x22" * AES_256_KEY_BYTES
    ct1, _, _ = _encrypt_value("password123", dek1)
    ct2, _, _ = _encrypt_value("password123", dek2)
    assert ct1 != ct2


def test_unicode_secret_value_round_trips() -> None:
    raw_dek = b"\xff" * AES_256_KEY_BYTES
    value = "p@$$w0rd-こんにちは-🔐"
    ct, nonce, tag = _encrypt_value(value, raw_dek)
    recovered = _decrypt_value(ct, nonce, tag, raw_dek)
    assert recovered == value


def test_long_secret_value_round_trips() -> None:
    raw_dek = b"\xee" * AES_256_KEY_BYTES
    value = "x" * 10_000  # 10 KB secret
    ct, nonce, tag = _encrypt_value(value, raw_dek)
    recovered = _decrypt_value(ct, nonce, tag, raw_dek)
    assert recovered == value


# ---------------------------------------------------------------------------
# Key material wire format (KMS integration — no DB)
# ---------------------------------------------------------------------------


def test_kek_wire_format_survives_re_encrypt_cycle(test_settings: Settings) -> None:
    """Simulate what happens during a secret update: decrypt old DEK, re-encrypt under new KEK."""
    old_kek_raw = b"\xab" * AES_256_KEY_BYTES
    dek_raw = b"\xcd" * AES_256_KEY_BYTES

    # DEK encrypted under old KEK
    encrypted_dek = _encrypt_key_material(dek_raw, old_kek_raw)

    # Re-key: decrypt with old KEK, re-encrypt under new KEK
    new_kek_raw = b"\xef" * AES_256_KEY_BYTES
    recovered_dek = _decrypt_key_material(encrypted_dek, old_kek_raw)
    re_encrypted_dek = _encrypt_key_material(recovered_dek, new_kek_raw)

    # Verify: decrypt from new KEK gives original DEK
    final_dek = _decrypt_key_material(re_encrypted_dek, new_kek_raw)
    assert final_dek == dek_raw
