import logging
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI

from app.api.deps import settings_provider
from app.api.v1.router import api_router
from app.core.config import Settings, get_settings
from app.core.logging import configure_logging

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    configure_logging(settings)
    logger.info("Starting %s in %s mode", settings.app_name, settings.app_env)
    yield
    logger.info("Stopping %s", settings.app_name)


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved_settings = settings or get_settings()

    app = FastAPI(
        title=f"{resolved_settings.app_name} API",
        version="0.1.0",
        description="Internal security-team style secret management API.",
        lifespan=lifespan,
    )
    app.include_router(api_router, prefix=resolved_settings.api_v1_prefix)
    app.include_router(api_router)
    app.dependency_overrides[settings_provider] = lambda: resolved_settings
    return app


app = create_app()
