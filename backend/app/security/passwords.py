from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError

_password_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    if not password:
        raise ValueError("password must not be empty")
    return _password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    if not password or not password_hash:
        return False
    try:
        return _password_hasher.verify(password_hash, password)
    except (VerifyMismatchError, VerificationError):
        return False


def password_hash_needs_rehash(password_hash: str) -> bool:
    return _password_hasher.check_needs_rehash(password_hash)
