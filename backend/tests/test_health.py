from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


def test_health_endpoint_returns_service_status() -> None:
    settings = Settings(APP_ENV="test")
    client = TestClient(create_app(settings))

    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "Sentinel Vault",
        "environment": "test",
        "version": "0.1.0",
    }


def test_legacy_root_health_endpoint_is_available_for_simple_uptime_checks() -> None:
    settings = Settings(APP_ENV="test")
    client = TestClient(create_app(settings))

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
