"""Tests for Phase 9: Security headers and CORS."""

import pytest
from fastapi.testclient import TestClient
from app.core.config import Settings
from app.main import create_app

def test_security_headers():
    settings = Settings(APP_ENV="test")
    client = TestClient(create_app(settings))
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.headers.get("X-Content-Type-Options") == "nosniff"
    assert response.headers.get("X-Frame-Options") == "DENY"
    assert "Strict-Transport-Security" in response.headers
    assert "Content-Security-Policy" in response.headers
    assert response.headers.get("X-XSS-Protection") == "1; mode=block"

def test_cors_headers():
    settings = Settings(APP_ENV="test")
    client = TestClient(create_app(settings))
    response = client.options(
        "/api/v1/health",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"
