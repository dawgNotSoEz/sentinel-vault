import hashlib
import hmac


def hash_refresh_token(refresh_token: str, secret_key: str) -> str:
    if not refresh_token:
        raise ValueError("refresh token must not be empty")
    return hmac.new(
        key=secret_key.encode("utf-8"),
        msg=refresh_token.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).hexdigest()
