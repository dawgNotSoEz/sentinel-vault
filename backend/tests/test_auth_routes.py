from app.core.config import Settings
from app.main import create_app


def test_auth_routes_are_registered_in_openapi_contract() -> None:
    app = create_app(Settings(APP_ENV="test"))
    paths = set(app.openapi()["paths"])

    assert "/api/v1/auth/register" in paths
    assert "/api/v1/auth/login" in paths
    assert "/api/v1/auth/refresh" in paths
    assert "/api/v1/auth/logout" in paths
    assert "/api/v1/auth/me" in paths
