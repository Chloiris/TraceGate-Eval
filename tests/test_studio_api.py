from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from tracegate.config import PROJECT_ROOT
from tracegate.studio.app import SECURITY_HEADERS, create_app
from tracegate.studio.config import StudioSettings


TOKEN = "test-local-token-0123456789-abcdef"


def studio_settings(tmp_path: Path, **overrides: object) -> StudioSettings:
    values: dict[str, object] = {
        "host": "127.0.0.1",
        "port": 8765,
        "local_api_token": SecretStr(TOKEN),
        "database_url": f"sqlite+pysqlite:///{(tmp_path / 'studio.db').as_posix()}",
        "cors_origins": ("http://127.0.0.1:5173", "tauri://localhost"),
        "eval_root": PROJECT_ROOT,
        "github_token_configured": False,
        "model_api_key_configured": False,
    }
    values.update(overrides)
    return StudioSettings.model_validate(values)


@pytest.fixture
def client(tmp_path: Path) -> Iterator[TestClient]:
    with TestClient(create_app(studio_settings(tmp_path))) as active_client:
        yield active_client


def auth_headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {TOKEN}"}


def test_every_v1_endpoint_including_health_requires_bearer(client: TestClient) -> None:
    for path in ("/api/v1/health", "/api/v1/system/status", "/api/v1/settings", "/api/v1/onboarding"):
        response = client.get(path)
        assert response.status_code == 401
        assert response.json() == {
            "error": {"code": "unauthorized", "message": "A local bearer token is required."}
        }

    response = client.get(
        "/api/v1/health",
        headers={"Authorization": "Bearer wrong-token-that-is-long-enough"},
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


def test_health_reports_database_and_security_headers(client: TestClient) -> None:
    response = client.get("/api/v1/health", headers=auth_headers())
    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "tracegate-studio",
        "version": "0.1.0",
        "api_version": "v1",
        "database": {
            "state": "ready",
            "configured": True,
            "message": "Database is connected and migrated.",
            "detail": None,
        },
    }
    for name, value in SECURITY_HEADERS.items():
        assert response.headers[name] == value
    assert response.headers["cache-control"] == "no-store"


def test_cors_is_exact_and_never_wildcard(client: TestClient) -> None:
    allowed = client.get(
        "/api/v1/health",
        headers={**auth_headers(), "Origin": "http://127.0.0.1:5173"},
    )
    assert allowed.headers["access-control-allow-origin"] == "http://127.0.0.1:5173"

    tauri = client.get(
        "/api/v1/health",
        headers={**auth_headers(), "Origin": "tauri://localhost"},
    )
    assert tauri.headers["access-control-allow-origin"] == "tauri://localhost"

    denied = client.get(
        "/api/v1/health",
        headers={**auth_headers(), "Origin": "https://evil.example"},
    )
    assert "access-control-allow-origin" not in denied.headers


def test_system_status_exposes_unconfigured_services_without_fallback(client: TestClient) -> None:
    response = client.get("/api/v1/system/status", headers=auth_headers())
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "degraded"
    assert body["components"]["database"]["state"] == "ready"
    assert body["components"]["github"] == {
        "state": "not_configured",
        "configured": False,
        "message": "GitHub is not connected.",
        "detail": "Configure a GitHub credential before accessing private repositories or monitoring PRs.",
    }
    assert body["components"]["model"]["state"] == "not_configured"
    assert "no substitute provider was used" in body["components"]["model"]["detail"]
    assert body["components"]["eval"]["state"] == "ready"


def test_missing_eval_artifacts_are_unavailable_not_hardcoded(tmp_path: Path) -> None:
    settings = studio_settings(tmp_path, eval_root=tmp_path / "empty-eval")
    with TestClient(create_app(settings)) as active_client:
        response = active_client.get("/api/v1/system/status", headers=auth_headers())
    assert response.status_code == 200
    eval_status = response.json()["components"]["eval"]
    assert eval_status["state"] == "unavailable"
    assert eval_status["configured"] is False
    assert "Missing checked-in artifact" in eval_status["detail"]
    assert "160" not in eval_status["detail"]


def test_settings_put_is_partial_and_does_not_overwrite_model_fields(client: TestClient) -> None:
    initial = client.get("/api/v1/settings", headers=auth_headers()).json()
    assert initial["theme"] == "system"
    assert initial["model_provider"] is None

    response = client.put(
        "/api/v1/settings",
        headers=auth_headers(),
        json={
            "theme": "dark",
            "language": "en-US",
            "background_monitoring": True,
            "launch_at_startup": True,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["theme"] == "dark"
    assert body["language"] == "en-US"
    assert body["background_monitoring"] is True
    assert body["launch_at_startup"] is True
    assert body["model_provider"] is None

    invalid = client.put("/api/v1/settings", headers=auth_headers(), json={})
    assert invalid.status_code == 422
    assert invalid.json()["error"]["code"] == "validation_error"


def test_onboarding_get_and_put_use_persisted_state(client: TestClient) -> None:
    initial = client.get("/api/v1/onboarding", headers=auth_headers()).json()
    assert initial["completed"] is False
    assert initial["current_step"] == "welcome"
    assert initial["repository_added"] is False

    response = client.put(
        "/api/v1/onboarding",
        headers=auth_headers(),
        json={
            "current_step": "repository",
            "background_monitoring": True,
            "launch_at_startup": False,
        },
    )
    assert response.status_code == 200
    assert response.json()["current_step"] == "repository"
    assert response.json()["background_monitoring"] is True

    completed = client.put(
        "/api/v1/onboarding",
        headers=auth_headers(),
        json={"completed": True},
    )
    assert completed.status_code == 200
    assert completed.json()["completed"] is True
    assert completed.json()["current_step"] == "complete"
    assert completed.json()["completed_at"] is not None


def test_repository_crud_is_persisted_and_reports_unsynced_state(client: TestClient) -> None:
    created = client.post(
        "/api/v1/repositories",
        headers=auth_headers(),
        json={"full_name": "openai/openai-python", "monitoring_enabled": True},
    )
    assert created.status_code == 201
    repository = created.json()
    assert repository["connection_status"] == "not_connected"
    assert repository["clone_url"] == "https://github.com/openai/openai-python.git"

    listing = client.get("/api/v1/repositories", headers=auth_headers())
    assert listing.status_code == 200
    assert listing.json()["total"] == 1
    assert listing.json()["items"][0]["id"] == repository["id"]

    updated = client.put(
        f"/api/v1/repositories/{repository['id']}",
        headers=auth_headers(),
        json={"default_branch": "main", "monitoring_enabled": False},
    )
    assert updated.status_code == 200
    assert updated.json()["default_branch"] == "main"
    assert updated.json()["monitoring_enabled"] is False

    onboarding = client.get("/api/v1/onboarding", headers=auth_headers())
    assert onboarding.json()["repository_added"] is True

    duplicate = client.post(
        "/api/v1/repositories",
        headers=auth_headers(),
        json={"full_name": "openai/openai-python"},
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "repository_already_exists"

    deleted = client.delete(f"/api/v1/repositories/{repository['id']}", headers=auth_headers())
    assert deleted.status_code == 204
    missing = client.get(f"/api/v1/repositories/{repository['id']}", headers=auth_headers())
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "repository_not_found"


def test_docs_and_unknown_routes_are_not_exposed(client: TestClient) -> None:
    for path in ("/docs", "/redoc", "/openapi.json", "/api/v1/unknown"):
        response = client.get(path, headers=auth_headers())
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "not_found"
