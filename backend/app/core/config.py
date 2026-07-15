from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

Environment = Literal["development", "test", "staging", "production"]


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    The defaults are safe for local development only. Production deployments must
    override secrets and database URLs through environment variables.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = Field(default="Sentinel Vault", validation_alias="APP_NAME")
    app_env: Environment = Field(default="development", validation_alias="APP_ENV")
    api_v1_prefix: str = Field(default="/api/v1", validation_alias="API_V1_PREFIX")
    frontend_url: str = Field(default="http://localhost:3000", validation_alias="FRONTEND_URL")
    database_url: str = Field(
        default="postgresql+psycopg://sentinel:sentinel@localhost:5432/sentinel_vault",
        validation_alias="DATABASE_URL",
    )
    jwt_secret_key: str = Field(default="change-me-in-development", validation_alias="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", validation_alias="JWT_ALGORITHM")
    access_token_ttl_minutes: int = Field(default=15, validation_alias="ACCESS_TOKEN_TTL_MINUTES")
    refresh_token_ttl_days: int = Field(default=30, validation_alias="REFRESH_TOKEN_TTL_DAYS")
    master_key_id: str = Field(default="local-dev-master-key", validation_alias="MASTER_KEY_ID")
    # 32-byte master key encoded as 64 hex characters.
    # NEVER commit a real value here. Generate one with:
    #   python -c "import secrets; print(secrets.token_hex(32))"
    master_key_hex: str = Field(
        default="0" * 64,
        validation_alias="MASTER_KEY_HEX",
    )
    log_level: str = Field(default="INFO", validation_alias="LOG_LEVEL")

    @property
    def master_key_bytes(self) -> bytes:
        """Return the 32-byte master key decoded from hex."""
        try:
            raw = bytes.fromhex(self.master_key_hex)
        except ValueError as exc:
            raise ValueError("MASTER_KEY_HEX must be a valid 64-character hex string") from exc
        if len(raw) != 32:
            raise ValueError("MASTER_KEY_HEX must decode to exactly 32 bytes (64 hex chars)")
        return raw

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
