from fastapi import APIRouter, Depends

from app.api.deps import settings_provider
from app.core.config import Settings
from app.schemas.health import HealthResponse

router = APIRouter(prefix="/health", tags=["system"])


@router.get("", response_model=HealthResponse)
def health_check(settings: Settings = Depends(settings_provider)) -> HealthResponse:
    return HealthResponse(
        status="ok",
        service=settings.app_name,
        environment=settings.app_env,
        version="0.1.0",
    )
