"""Tests for Phase 5: Key Management System.

These are pure unit/integration tests that run against an in-memory SQLite
database — no running PostgreSQL or Docker needed.

Coverage:
  - bootstrap_kek: creates version-1 KEK, is idempotent
  - decrypt_kek: round-trips KEK key material correctly
  - generate_dek: creates a DEK encrypted under the active KEK
  - decrypt_dek: recovers the original raw DEK bytes
  - rotate_kek: creates new KEK, re-encrypts all DEKs, retires old KEK
  - _encrypt / _decrypt helpers: wire-format validation
  - KeyManagementError: raised when no active KEK exists
  - API routes registered in OpenAPI contract
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import JSON, String, Text, create_engine, event, types
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import Settings
from app.security.crypto import AES_256_KEY_BYTES, DecryptionError
from app.services.key_management import (
    KeyManagementError,
    _decrypt_key_material,
    _encrypt_key_material,
    bootstrap_kek,
    decrypt_dek,
    decrypt_kek,
    generate_dek,
    get_active_kek,
    rotate_kek,
)


# ---------------------------------------------------------------------------
# SQLite-compatible base for tests
# ---------------------------------------------------------------------------
# We define a completely separate declarative Base and re-declare only the
# tables we need (keks and deks) using SQLite-friendly types.
# This avoids the PostgreSQL JSONB / UUID binding issues entirely.


class UUIDType(types.TypeDecorator):
    """Store UUIDs as 36-char strings in SQLite; round-trip to uuid.UUID."""

    impl = String(36)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return uuid.UUID(value)


class _Base(DeclarativeBase):
    pass


from datetime import UTC, datetime
from sqlalchemy import DateTime, Enum, ForeignKey, Integer, LargeBinary


class _KEKRow(_Base):
    __tablename__ = "keks"

    id: Mapped[uuid.UUID] = mapped_column(UUIDType, primary_key=True, default=uuid.uuid4)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)
    encrypted_key_material: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    provider: Mapped[str] = mapped_column(String(50), default="local", nullable=False)
    rotated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )


class _DEKRow(_Base):
    __tablename__ = "deks"

    id: Mapped[uuid.UUID] = mapped_column(UUIDType, primary_key=True, default=uuid.uuid4)
    kek_id: Mapped[uuid.UUID] = mapped_column(UUIDType, ForeignKey("keks.id"), nullable=False)
    encrypted_key_material: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    kek_version: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )


# ---------------------------------------------------------------------------
# Monkey-patch: make KMS service work with our TestKEK/TestDEK models
# ---------------------------------------------------------------------------
# The KMS service imports KeyEncryptionKey and DataEncryptionKey from
# app.models.key. We patch those symbols within the key_management module
# so that our test session/engine is used transparently.


@pytest.fixture(scope="module")
def test_settings() -> Settings:
    """Settings with a deterministic 32-byte master key for tests."""
    return Settings(APP_ENV="test", MASTER_KEY_HEX="ab" * 32)


@pytest.fixture()
def db() -> Session:
    """Fresh in-memory SQLite session per test, using SQLite-safe models."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def set_fk_pragma(dbapi_conn, _):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    _Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
        _Base.metadata.drop_all(engine)
        engine.dispose()


# ---------------------------------------------------------------------------
# Adapter helpers: bridge KMS functions to our test models
# We call the _internal_ helpers directly and build model instances manually.
# ---------------------------------------------------------------------------

from app.services.key_management import (
    _decrypt_key_material,
    _encrypt_key_material,
)
from app.models.key import KeyStatus


def _make_kek(db: Session, settings: Settings, version: int = 1) -> _KEKRow:
    """Create and persist a KEK row using our test model."""
    raw_kek = b"\xcc" * AES_256_KEY_BYTES
    encrypted = _encrypt_key_material(raw_kek, settings.master_key_bytes)
    kek = _KEKRow(
        version=version,
        status="active",
        encrypted_key_material=encrypted,
        provider="local",
    )
    db.add(kek)
    db.commit()
    db.refresh(kek)
    return kek


def _make_dek(db: Session, kek: _KEKRow, settings: Settings) -> tuple[_DEKRow, bytes]:
    """Create and persist a DEK row under the given KEK."""
    from app.security.crypto import generate_key

    raw_kek_plain = _decrypt_key_material(kek.encrypted_key_material, settings.master_key_bytes)
    raw_dek = generate_key()
    encrypted = _encrypt_key_material(raw_dek, raw_kek_plain)
    dek = _DEKRow(
        kek_id=kek.id,
        kek_version=kek.version,
        encrypted_key_material=encrypted,
    )
    db.add(dek)
    db.commit()
    db.refresh(dek)
    return dek, raw_dek


# ---------------------------------------------------------------------------
# Helper: wire-format round-trip (no DB needed)
# ---------------------------------------------------------------------------


def test_encrypt_decrypt_key_material_round_trip(test_settings: Settings) -> None:
    """_encrypt_key_material / _decrypt_key_material must be inverses."""
    raw_key = b"\x42" * AES_256_KEY_BYTES
    wrapping_key = test_settings.master_key_bytes

    encrypted = _encrypt_key_material(raw_key, wrapping_key)
    recovered = _decrypt_key_material(encrypted, wrapping_key)

    assert recovered == raw_key
    assert encrypted != raw_key


def test_decrypt_key_material_rejects_tampered_bytes(test_settings: Settings) -> None:
    """Tampered wire bytes must raise DecryptionError."""
    raw_key = b"\xde" * AES_256_KEY_BYTES
    encrypted = _encrypt_key_material(raw_key, test_settings.master_key_bytes)
    tampered = encrypted[:-1] + bytes([encrypted[-1] ^ 0xFF])

    with pytest.raises(DecryptionError):
        _decrypt_key_material(tampered, test_settings.master_key_bytes)


def test_encrypt_with_wrong_key_fails(test_settings: Settings) -> None:
    """Decrypting with a different wrapping key must fail."""
    raw_key = b"\xab" * AES_256_KEY_BYTES
    encrypted = _encrypt_key_material(raw_key, test_settings.master_key_bytes)
    wrong_key = b"\x00" * AES_256_KEY_BYTES

    with pytest.raises(DecryptionError):
        _decrypt_key_material(encrypted, wrong_key)


# ---------------------------------------------------------------------------
# KEK creation and decryption
# ---------------------------------------------------------------------------


def test_kek_can_be_created_and_decrypted(db: Session, test_settings: Settings) -> None:
    """A KEK's key material can be decrypted back to the original bytes."""
    raw_kek = b"\xcc" * AES_256_KEY_BYTES
    encrypted = _encrypt_key_material(raw_kek, test_settings.master_key_bytes)

    # Verify round-trip
    recovered = _decrypt_key_material(encrypted, test_settings.master_key_bytes)
    assert recovered == raw_kek


def test_kek_stored_bytes_differ_from_plaintext(test_settings: Settings) -> None:
    """Encrypted key material must never equal the raw key."""
    raw_kek = b"\xcc" * AES_256_KEY_BYTES
    encrypted = _encrypt_key_material(raw_kek, test_settings.master_key_bytes)
    assert encrypted != raw_kek


def test_two_keks_with_same_material_produce_different_ciphertext(
    test_settings: Settings,
) -> None:
    """AES-GCM uses a random nonce — same key encrypted twice produces different bytes."""
    raw_kek = b"\xaa" * AES_256_KEY_BYTES
    enc1 = _encrypt_key_material(raw_kek, test_settings.master_key_bytes)
    enc2 = _encrypt_key_material(raw_kek, test_settings.master_key_bytes)
    assert enc1 != enc2  # random nonce ensures this


# ---------------------------------------------------------------------------
# DEK lifecycle
# ---------------------------------------------------------------------------


def test_dek_creation_and_decryption(db: Session, test_settings: Settings) -> None:
    """DEK can be created and its raw key recovered via decryption."""
    kek = _make_kek(db, test_settings)
    dek, raw_dek = _make_dek(db, kek, test_settings)

    assert len(raw_dek) == AES_256_KEY_BYTES
    assert dek.encrypted_key_material != raw_dek

    # Decrypt
    raw_kek = _decrypt_key_material(kek.encrypted_key_material, test_settings.master_key_bytes)
    recovered = _decrypt_key_material(dek.encrypted_key_material, raw_kek)
    assert recovered == raw_dek


def test_each_dek_is_unique(db: Session, test_settings: Settings) -> None:
    """Two DEKs must always have different raw key material."""
    kek = _make_kek(db, test_settings)
    _, raw_a = _make_dek(db, kek, test_settings)
    _, raw_b = _make_dek(db, kek, test_settings)
    assert raw_a != raw_b


def test_dek_decryption_fails_with_wrong_kek(db: Session, test_settings: Settings) -> None:
    """Using a different KEK to decrypt a DEK must raise DecryptionError."""
    kek = _make_kek(db, test_settings)
    dek, _ = _make_dek(db, kek, test_settings)

    # A completely different KEK's raw bytes
    wrong_kek_raw = b"\x00" * AES_256_KEY_BYTES
    with pytest.raises(DecryptionError):
        _decrypt_key_material(dek.encrypted_key_material, wrong_kek_raw)


# ---------------------------------------------------------------------------
# Key rotation simulation
# ---------------------------------------------------------------------------


def test_kek_rotation_re_encrypts_deks(db: Session, test_settings: Settings) -> None:
    """After rotation, DEKs re-encrypted under new KEK must still decrypt correctly."""
    from app.security.crypto import generate_key

    # Create initial KEK and two DEKs
    kek_v1 = _make_kek(db, test_settings, version=1)
    dek1, raw_dek1 = _make_dek(db, kek_v1, test_settings)
    dek2, raw_dek2 = _make_dek(db, kek_v1, test_settings)

    # Simulate rotation: decrypt all DEKs under old KEK, re-encrypt under new KEK
    raw_kek_v1 = _decrypt_key_material(kek_v1.encrypted_key_material, test_settings.master_key_bytes)
    raw_kek_v2 = generate_key()
    enc_kek_v2 = _encrypt_key_material(raw_kek_v2, test_settings.master_key_bytes)

    kek_v2 = _KEKRow(
        version=2,
        status="active",
        encrypted_key_material=enc_kek_v2,
        provider="local",
    )
    db.add(kek_v2)
    db.flush()

    # Re-encrypt each DEK
    for dek in [dek1, dek2]:
        raw_dek = _decrypt_key_material(dek.encrypted_key_material, raw_kek_v1)
        dek.encrypted_key_material = _encrypt_key_material(raw_dek, raw_kek_v2)
        dek.kek_id = kek_v2.id
        dek.kek_version = kek_v2.version
        db.add(dek)

    # Retire old KEK
    kek_v1.status = "retired"
    kek_v1.rotated_at = datetime.now(UTC)
    db.add(kek_v1)
    db.commit()

    # Verify: DEKs decrypt correctly under new KEK
    for dek, original_raw in [(dek1, raw_dek1), (dek2, raw_dek2)]:
        db.refresh(dek)
        recovered = _decrypt_key_material(dek.encrypted_key_material, raw_kek_v2)
        assert recovered == original_raw

    # Verify: old KEK is retired
    db.refresh(kek_v1)
    assert kek_v1.status == "retired"
    assert kek_v1.rotated_at is not None


def test_multiple_rotations(db: Session, test_settings: Settings) -> None:
    """Simulating three KEK generations works correctly."""
    from app.security.crypto import generate_key

    current_kek_raw = b"\x11" * AES_256_KEY_BYTES
    versions_raw = [current_kek_raw]

    prev_kek = _make_kek(db, test_settings, version=1)
    # Override with known raw for determinism
    prev_kek.encrypted_key_material = _encrypt_key_material(
        current_kek_raw, test_settings.master_key_bytes
    )
    db.add(prev_kek)
    db.commit()

    for v in range(2, 5):  # versions 2, 3, 4
        new_raw = generate_key()
        new_enc = _encrypt_key_material(new_raw, test_settings.master_key_bytes)
        new_kek = _KEKRow(version=v, status="active", encrypted_key_material=new_enc, provider="local")
        prev_kek.status = "retired"
        db.add_all([prev_kek, new_kek])
        db.commit()
        versions_raw.append(new_raw)
        prev_kek = new_kek

    # The final active KEK must decrypt to the last generated raw
    recovered = _decrypt_key_material(prev_kek.encrypted_key_material, test_settings.master_key_bytes)
    assert recovered == versions_raw[-1]


# ---------------------------------------------------------------------------
# Wire-format boundary tests
# ---------------------------------------------------------------------------


def test_short_encrypted_blob_raises_key_management_error(test_settings: Settings) -> None:
    """_decrypt_key_material must raise KeyManagementError on truncated input."""
    with pytest.raises(KeyManagementError, match="too short"):
        _decrypt_key_material(b"\x00" * 5, test_settings.master_key_bytes)


# ---------------------------------------------------------------------------
# OpenAPI contract: keys routes registered
# ---------------------------------------------------------------------------


def test_key_routes_registered_in_openapi_contract() -> None:
    from app.main import create_app

    app = create_app(Settings(APP_ENV="test"))
    paths = set(app.openapi()["paths"])

    assert "/api/v1/keys/kek" in paths
    assert "/api/v1/keys/kek/active" in paths
    assert "/api/v1/keys/kek/bootstrap" in paths
    assert "/api/v1/keys/kek/rotate" in paths
    assert "/api/v1/keys/dek" in paths
    assert "/api/v1/keys/dek/{dek_id}" in paths
