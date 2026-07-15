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
    database_url: str = Field(
        default="postgresql+psycopg://sentinel:sentinel@localhost:5432/sentinel_vault",
        validation_alias="DATABASE_URL",
    )
    jwt_secret_key: str = Field(default="change-me-in-development", validation_alias="JWT_SECRET_KEY")
    master_key_id: str = Field(default="local-dev-master-key", validation_alias="MASTER_KEY_ID")
    log_level: str = Field(default="INFO", validation_alias="LOG_LEVEL")

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
