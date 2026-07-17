import pytest
from app.core.config import Settings


def test_settings_defaults_are_development_safe(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("APP_ENV", raising=False)
    settings = Settings(_env_file=None)

    assert settings.app_name == "Sentinel Vault"
    assert settings.app_env == "development"
    assert settings.api_v1_prefix == "/api/v1"
    assert settings.is_production is False


def test_settings_can_be_overridden_for_tests() -> None:
    settings = Settings(APP_NAME="Sentinel Vault Test", APP_ENV="test", LOG_LEVEL="DEBUG")

    assert settings.app_name == "Sentinel Vault Test"
    assert settings.app_env == "test"
    assert settings.log_level == "DEBUG"
