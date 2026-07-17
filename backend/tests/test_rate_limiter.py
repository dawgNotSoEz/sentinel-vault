"""Tests for Phase 9: Rate limiting."""

from fastapi.testclient import TestClient
from app.core.config import Settings
from app.main import create_app
from app.db.session import get_db

# We need a mock db to pass dependency injection
from unittest.mock import MagicMock

def test_rate_limiter_auth_register():
    settings = Settings(APP_ENV="test")
    app = create_app(settings)
    app.dependency_overrides[get_db] = lambda: MagicMock()
    client = TestClient(app)
    # The register endpoint is limited to 5/minute.
    # We will send 6 requests. The 6th should fail with 429.
    
    payload = {
        "email": "ratelimit@example.com",
        "password": "Password123!",
        "full_name": "Rate Limit Test"
    }

    # In a fast test environment, slowapi uses in-memory limits.
    # Note: registering same user will give 409 Conflict after the first one,
    # but the rate limiter runs *before* the business logic, so we will still
    # hit the 429 after 5 requests.

    for _ in range(5):
        client.post("/api/v1/auth/register", json=payload)
    
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 429
    assert response.json() == {"detail": "Rate limit exceeded"}
