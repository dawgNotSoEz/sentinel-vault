from fastapi import APIRouter

from app.api.v1.audit import router as audit_router
from app.api.v1.auth import router as auth_router
from app.api.v1.health import router as health_router
from app.api.v1.keys import router as keys_router
from app.api.v1.secrets import router as secrets_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(auth_router)
api_router.include_router(keys_router)
api_router.include_router(secrets_router)
api_router.include_router(audit_router)
