from __future__ import annotations

import base64
from dataclasses import dataclass
from secrets import token_bytes

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

AES_256_KEY_BYTES = 32
AES_GCM_NONCE_BYTES = 12
AES_GCM_TAG_BYTES = 16


class EncryptionError(ValueError):
    pass


class DecryptionError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class EncryptedPayload:
    ciphertext: bytes
    nonce: bytes
    auth_tag: bytes

    def combined_ciphertext(self) -> bytes:
        return self.ciphertext + self.auth_tag

    def as_base64_dict(self) -> dict[str, str]:
        return {
            "ciphertext": base64.b64encode(self.ciphertext).decode("ascii"),
            "nonce": base64.b64encode(self.nonce).decode("ascii"),
            "auth_tag": base64.b64encode(self.auth_tag).decode("ascii"),
        }

    @classmethod
    def from_base64_dict(cls, payload: dict[str, str]) -> EncryptedPayload:
        return cls(
            ciphertext=base64.b64decode(payload["ciphertext"], validate=True),
            nonce=base64.b64decode(payload["nonce"], validate=True),
            auth_tag=base64.b64decode(payload["auth_tag"], validate=True),
        )


def generate_key() -> bytes:
    return token_bytes(AES_256_KEY_BYTES)


def generate_nonce() -> bytes:
    return token_bytes(AES_GCM_NONCE_BYTES)


def _validate_key(key: bytes) -> None:
    if len(key) != AES_256_KEY_BYTES:
        raise EncryptionError("AES-256-GCM key must be exactly 32 bytes")


def _validate_nonce(nonce: bytes) -> None:
    if len(nonce) != AES_GCM_NONCE_BYTES:
        raise EncryptionError("AES-GCM nonce must be exactly 12 bytes")


def encrypt(plaintext: bytes, key: bytes, aad: bytes | None = None) -> EncryptedPayload:
    if not plaintext:
        raise EncryptionError("plaintext must not be empty")
    _validate_key(key)
    nonce = generate_nonce()
    encrypted = AESGCM(key).encrypt(nonce, plaintext, aad)
    return EncryptedPayload(
        ciphertext=encrypted[:-AES_GCM_TAG_BYTES],
        nonce=nonce,
        auth_tag=encrypted[-AES_GCM_TAG_BYTES:],
    )


def decrypt(payload: EncryptedPayload, key: bytes, aad: bytes | None = None) -> bytes:
    _validate_key(key)
    _validate_nonce(payload.nonce)
    if len(payload.auth_tag) != AES_GCM_TAG_BYTES:
        raise DecryptionError("AES-GCM authentication tag must be exactly 16 bytes")
    try:
        return AESGCM(key).decrypt(payload.nonce, payload.combined_ciphertext(), aad)
    except InvalidTag as exc:
        raise DecryptionError("ciphertext authentication failed") from exc
