"""Tests for health endpoints."""

from typing import Any

from fastapi.testclient import TestClient

from app.config import AppEnvironment, Settings
from app.main import create_app
from app.middleware import REQUEST_ID_HEADER


def build_client() -> TestClient:
    settings = Settings()
    return TestClient(create_app(settings))


def response_json(response: Any) -> dict[str, Any]:
    data = response.json()
    assert isinstance(data, dict)
    return data


def test_root_returns_service_information() -> None:
    client = build_client()

    response = client.get("/")
    data = response_json(response)

    assert response.status_code == 200
    assert data == {
        "app_name": "Enterprise Multi-Agent OS",
        "environment": AppEnvironment.DEVELOPMENT,
        "version": "0.1.0",
        "docs_url": "/docs",
        "health_url": "/health",
    }


def test_health_returns_ok_status() -> None:
    client = build_client()

    response = client.get("/health")
    data = response_json(response)

    assert response.status_code == 200
    assert data["status"] == "ok"
    assert data["app_name"] == "Enterprise Multi-Agent OS"
    assert data["environment"] == AppEnvironment.DEVELOPMENT
    assert data["version"] == "0.1.0"
    assert isinstance(data["timestamp"], str)


def test_ready_returns_lightweight_readiness() -> None:
    client = build_client()

    response = client.get("/ready")
    data = response_json(response)

    assert response.status_code == 200
    assert data == {
        "status": "ready",
        "checks": {
            "application": "ready",
            "external_services": "not_configured",
        },
    }


def test_live_returns_alive_status() -> None:
    client = build_client()

    response = client.get("/live")
    data = response_json(response)

    assert response.status_code == 200
    assert data["status"] == "alive"
    assert isinstance(data["timestamp"], str)


def test_health_response_includes_request_id_header() -> None:
    client = build_client()

    response = client.get("/health")

    assert response.status_code == 200
    assert response.headers[REQUEST_ID_HEADER]
