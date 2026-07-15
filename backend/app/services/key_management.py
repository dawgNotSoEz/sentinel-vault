"""Key Management Service — Envelope Encryption implementation.

Hierarchy:
    Master Key (env var, 32 bytes)
        └── KeyEncryptionKey (KEK, stored encrypted in DB)
                └── DataEncryptionKey (DEK, stored encrypted in DB)
                        └── SecretVersion (plaintext encrypted with DEK at rest)

Rules enforced here:
  - Master key NEVER touches the database.
  - DEKs are ALWAYS stored encrypted — never as plaintext.
  - Each call to `generate_dek` creates a unique, single-use DEK.
  - KEK rotation re-encrypts every live DEK before retiring the old KEK.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models.key import DataEncryptionKey, KeyEncryptionKey, KeyStatus
from app.security.crypto import (
    EncryptedPayload,
    decrypt,
    encrypt,
    generate_key,
)

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class KeyManagementError(RuntimeError):
    """Raised when the KMS cannot complete an operation safely."""


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _encrypt_key_material(raw_key: bytes, wrapping_key: bytes) -> bytes:
    """AES-256-GCM encrypt `raw_key` under `wrapping_key`.

    Returns the wire format: ``nonce || ciphertext || auth_tag`` as raw bytes.
    We store it as LargeBinary and never expose it outside this module.
    """
    payload = encrypt(raw_key, wrapping_key)
    # Compact wire format: nonce (12 B) + ciphertext (32 B) + auth_tag (16 B) = 60 B
    return payload.nonce + payload.ciphertext + payload.auth_tag


def _decrypt_key_material(encrypted: bytes, wrapping_key: bytes) -> bytes:
    """Reverse of `_encrypt_key_material`. Raises DecryptionError on tamper."""
    from app.security.crypto import AES_GCM_NONCE_BYTES, AES_GCM_TAG_BYTES

    if len(encrypted) < AES_GCM_NONCE_BYTES + AES_GCM_TAG_BYTES + 1:
        raise KeyManagementError("encrypted key material is too short to be valid")

    nonce = encrypted[:AES_GCM_NONCE_BYTES]
    auth_tag = encrypted[-AES_GCM_TAG_BYTES:]
    ciphertext = encrypted[AES_GCM_NONCE_BYTES:-AES_GCM_TAG_BYTES]

    payload = EncryptedPayload(ciphertext=ciphertext, nonce=nonce, auth_tag=auth_tag)
    return decrypt(payload, wrapping_key)


# ---------------------------------------------------------------------------
# KEK operations
# ---------------------------------------------------------------------------


def get_active_kek(db: Session) -> KeyEncryptionKey | None:
    """Return the current active KEK row, or None if none exists."""
    return db.scalar(
        select(KeyEncryptionKey)
        .where(KeyEncryptionKey.status == KeyStatus.ACTIVE)
        .order_by(KeyEncryptionKey.version.desc())
        .limit(1)
    )


def bootstrap_kek(db: Session, settings: Settings) -> KeyEncryptionKey:
    """Create the very first KEK (version 1) if none exists.

    Called once during first startup or test setup.  It is idempotent — if an
    active KEK already exists it returns it without creating a new one.
    """
    existing = get_active_kek(db)
    if existing is not None:
        return existing

    raw_kek = generate_key()  # 32 random bytes
    encrypted_material = _encrypt_key_material(raw_kek, settings.master_key_bytes)

    kek = KeyEncryptionKey(
        version=1,
        status=KeyStatus.ACTIVE,
        encrypted_key_material=encrypted_material,
        provider="local",
    )
    db.add(kek)
    db.commit()
    db.refresh(kek)
    logger.info("Bootstrapped KEK version 1 (id=%s)", kek.id)
    return kek


def decrypt_kek(kek: KeyEncryptionKey, settings: Settings) -> bytes:
    """Decrypt and return the raw 32-byte key for `kek`.

    The returned bytes must NOT be stored — use them ephemerally.
    """
    return _decrypt_key_material(kek.encrypted_key_material, settings.master_key_bytes)


# ---------------------------------------------------------------------------
# DEK operations
# ---------------------------------------------------------------------------


def generate_dek(db: Session, settings: Settings) -> tuple[DataEncryptionKey, bytes]:
    """Generate a new DEK encrypted under the active KEK.

    Returns:
        (dek_row, raw_dek_bytes) — the caller uses `raw_dek_bytes` to encrypt
        the secret and MUST NOT persist the raw bytes.

    Raises:
        KeyManagementError: if no active KEK exists (call bootstrap_kek first).
    """
    kek = get_active_kek(db)
    if kek is None:
        raise KeyManagementError(
            "No active KEK found. Call bootstrap_kek() before generating DEKs."
        )

    raw_kek = decrypt_kek(kek, settings)
    raw_dek = generate_key()  # 32 random bytes — brand new, used once
    encrypted_material = _encrypt_key_material(raw_dek, raw_kek)

    dek = DataEncryptionKey(
        kek_id=kek.id,
        kek_version=kek.version,
        encrypted_key_material=encrypted_material,
    )
    db.add(dek)
    db.commit()
    db.refresh(dek)
    logger.debug("Generated DEK id=%s under KEK version=%s", dek.id, kek.version)
    return dek, raw_dek


def decrypt_dek(dek: DataEncryptionKey, db: Session, settings: Settings) -> bytes:
    """Decrypt and return the raw 32-byte key for `dek`.

    Looks up the KEK that originally encrypted this DEK.

    Raises:
        KeyManagementError: if the parent KEK is missing or compromised.
    """
    kek = db.get(KeyEncryptionKey, dek.kek_id)
    if kek is None:
        raise KeyManagementError(f"KEK id={dek.kek_id} not found for DEK id={dek.id}")
    if kek.status == KeyStatus.COMPROMISED:
        raise KeyManagementError(
            f"KEK version={kek.version} is marked COMPROMISED — cannot decrypt DEK id={dek.id}"
        )

    raw_kek = decrypt_kek(kek, settings)
    return _decrypt_key_material(dek.encrypted_key_material, raw_kek)


# ---------------------------------------------------------------------------
# Key rotation
# ---------------------------------------------------------------------------


def rotate_kek(db: Session, settings: Settings) -> KeyEncryptionKey:
    """Rotate the active KEK.

    Steps (designed to be safe if interrupted):
      1. Decrypt all DEKs using the OLD KEK.
      2. Generate a NEW KEK (version = old_version + 1).
      3. Re-encrypt every DEK under the NEW KEK.
      4. Retire the OLD KEK (status → RETIRED).
      5. Commit everything atomically.

    If this function raises at any point before the final commit, the database
    is left unchanged — the old KEK remains active.

    Returns:
        The newly created active KEK row.

    Raises:
        KeyManagementError: if no active KEK exists or re-encryption fails.
    """
    old_kek = get_active_kek(db)
    if old_kek is None:
        raise KeyManagementError("Cannot rotate — no active KEK found.")

    # Step 1 — decrypt all DEKs under the current KEK while we still can
    deks: list[DataEncryptionKey] = list(
        db.scalars(
            select(DataEncryptionKey).where(DataEncryptionKey.kek_id == old_kek.id)
        )
    )
    raw_old_kek = decrypt_kek(old_kek, settings)
    plaintext_deks: list[tuple[DataEncryptionKey, bytes]] = []
    for dek in deks:
        raw_dek = _decrypt_key_material(dek.encrypted_key_material, raw_old_kek)
        plaintext_deks.append((dek, raw_dek))

    # Step 2 — generate the new KEK
    raw_new_kek = generate_key()
    new_encrypted_material = _encrypt_key_material(raw_new_kek, settings.master_key_bytes)
    new_kek = KeyEncryptionKey(
        version=old_kek.version + 1,
        status=KeyStatus.ACTIVE,
        encrypted_key_material=new_encrypted_material,
        provider="local",
    )
    db.add(new_kek)
    db.flush()  # get new_kek.id without committing yet

    # Step 3 — re-encrypt each DEK under the new KEK
    for dek, raw_dek in plaintext_deks:
        dek.encrypted_key_material = _encrypt_key_material(raw_dek, raw_new_kek)
        dek.kek_id = new_kek.id
        dek.kek_version = new_kek.version
        db.add(dek)

    # Step 4 — retire the old KEK
    from datetime import UTC, datetime

    old_kek.status = KeyStatus.RETIRED
    old_kek.rotated_at = datetime.now(UTC)
    db.add(old_kek)

    # Step 5 — single atomic commit
    db.commit()
    db.refresh(new_kek)
    logger.info(
        "KEK rotated: version %s → %s (re-encrypted %d DEKs)",
        old_kek.version,
        new_kek.version,
        len(deks),
    )
    return new_kek
