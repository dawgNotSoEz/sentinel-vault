import pytest

from app.security.crypto import (
    AES_256_KEY_BYTES,
    AES_GCM_NONCE_BYTES,
    AES_GCM_TAG_BYTES,
    DecryptionError,
    EncryptedPayload,
    EncryptionError,
    decrypt,
    encrypt,
    generate_key,
    generate_nonce,
)


def test_generate_key_and_nonce_sizes() -> None:
    assert len(generate_key()) == AES_256_KEY_BYTES
    assert len(generate_nonce()) == AES_GCM_NONCE_BYTES
    assert generate_key() != generate_key()
    assert generate_nonce() != generate_nonce()


def test_encrypt_decrypt_round_trip() -> None:
    key = generate_key()
    plaintext = b"database-password=super-secret"
    aad = b"secret-id:123"

    payload = encrypt(plaintext, key, aad=aad)
    decrypted = decrypt(payload, key, aad=aad)

    assert decrypted == plaintext
    assert payload.ciphertext != plaintext
    assert len(payload.nonce) == AES_GCM_NONCE_BYTES
    assert len(payload.auth_tag) == AES_GCM_TAG_BYTES


def test_decryption_fails_when_ciphertext_is_tampered() -> None:
    key = generate_key()
    payload = encrypt(b"sensitive value", key)
    tampered = EncryptedPayload(
        ciphertext=payload.ciphertext[:-1] + bytes([payload.ciphertext[-1] ^ 1]),
        nonce=payload.nonce,
        auth_tag=payload.auth_tag,
    )

    with pytest.raises(DecryptionError):
        decrypt(tampered, key)


def test_decryption_fails_with_wrong_aad() -> None:
    key = generate_key()
    payload = encrypt(b"sensitive value", key, aad=b"correct-context")

    with pytest.raises(DecryptionError):
        decrypt(payload, key, aad=b"wrong-context")


def test_invalid_key_size_is_rejected() -> None:
    with pytest.raises(EncryptionError):
        encrypt(b"plaintext", b"too-short")


def test_empty_plaintext_is_rejected() -> None:
    with pytest.raises(EncryptionError):
        encrypt(b"", generate_key())


def test_payload_base64_serialization_round_trip() -> None:
    key = generate_key()
    payload = encrypt(b"api-key-value", key)

    encoded = payload.as_base64_dict()
    restored = EncryptedPayload.from_base64_dict(encoded)

    assert restored == payload
    assert decrypt(restored, key) == b"api-key-value"
