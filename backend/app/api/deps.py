from collections.abc import Generator

from app.core.config import Settings, get_settings


def settings_provider() -> Generator[Settings, None, None]:
    """FastAPI dependency wrapper for application settings."""

    yield get_settings()
