from __future__ import annotations

import hashlib
import hmac
import json
import subprocess
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from tracegate.config import PROJECT_ROOT
from tracegate.studio.app import SECURITY_HEADERS, create_app
from tracegate.studio.config import StudioSettings
from tracegate.github import GitHubRateLimit, PullRequestData
from tracegate.studio.models import PullRequest


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
        "message": "GitHub 尚未连接",
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


def test_repository_index_and_graph_use_real_local_git_content(client: TestClient, tmp_path: Path) -> None:
    repository_path = tmp_path / "workspace"
    repository_path.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repository_path, check=True)
    subprocess.run(["git", "config", "user.email", "tracegate@example.invalid"], cwd=repository_path, check=True)
    subprocess.run(["git", "config", "user.name", "TraceGate Test"], cwd=repository_path, check=True)
    (repository_path / "main.py").write_text("def indexed_function():\n    return 1\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=repository_path, check=True)
    subprocess.run(["git", "commit", "-qm", "index fixture"], cwd=repository_path, check=True)

    created = client.post(
        "/api/v1/repositories",
        headers=auth_headers(),
        json={"full_name": "acme/indexed", "local_path": str(repository_path)},
    ).json()
    indexed = client.post(f"/api/v1/repositories/{created['id']}/index", headers=auth_headers())
    assert indexed.status_code == 200
    assert indexed.json()["file_count"] == 1
    assert indexed.json()["symbol_count"] == 1
    assert indexed.json()["commit_sha"]

    graph = client.get(f"/api/v1/repositories/{created['id']}/graph", headers=auth_headers())
    assert graph.status_code == 200
    assert graph.json()["index_version"] == indexed.json()["id"]
    assert any(node["label"] == "indexed_function" for node in graph.json()["nodes"])
    assert graph.json()["vector_search_enabled"] is False

    retrieval = client.get(
        f"/api/v1/repositories/{created['id']}/search",
        headers=auth_headers(),
        params={"query": "indexed_function"},
    )
    assert retrieval.status_code == 200
    assert retrieval.json()["hits"][0]["path"] == "main.py"
    assert {hit["source"] for hit in retrieval.json()["hits"]} & {"symbol", "fts5"}
    assert retrieval.json()["vector_search_enabled"] is False
    assert "no keyword result is labelled as vector" in retrieval.json()["vector_search_message"]

    with client.app.state.database.session_factory() as session:
        pull_request = PullRequest(
            repository_id=created["id"],
            number=3,
            title="Indexed PR",
            state="open",
            url="https://github.com/acme/indexed/pull/3",
            base_sha="a" * 40,
            head_sha=indexed.json()["commit_sha"],
        )
        session.add(pull_request)
        session.commit()
        session.refresh(pull_request)
        pull_request_id = pull_request.id
    blocked = client.post(f"/api/v1/pull-requests/{pull_request_id}/analyze", headers=auth_headers())
    assert blocked.status_code == 409
    assert blocked.json()["error"]["code"] == "model_not_configured"
    assert client.get("/api/v1/runs", headers=auth_headers()).json()["total"] == 0


def test_evaluation_and_registry_endpoints_are_derived_from_real_state(client: TestClient) -> None:
    evaluation = client.get("/api/v1/evaluations", headers=auth_headers())
    assert evaluation.status_code == 200
    body = evaluation.json()
    assert body["is_real_dataset"] is True
    assert body["case_count"] == 19
    assert body["claimbench_run_count"] == 160
    assert body["status_distribution"] == {
        "active": 12,
        "conflicting": 2,
        "stale": 2,
        "unknown": 3,
    }
    assert body["metrics"]["unsafe_allow_rate"] == 0.0
    assert len(body["cases"]) == 160
    assert all(artifact["sha256"] for artifact in body["artifacts"])

    agents = client.get("/api/v1/agents", headers=auth_headers())
    assert agents.status_code == 200
    assert [agent["name"] for agent in agents.json()] == [
        "Planner",
        "Repository Retriever",
        "Context Resolver",
        "Code Analyst",
        "Risk Reviewer",
        "Verifier",
        "Report Composer",
    ]

    tools = client.get("/api/v1/tools", headers=auth_headers())
    assert tools.status_code == 200
    descriptors = {tool["name"]: tool for tool in tools.json()}
    assert {"read_file", "search_code", "get_git_diff", "run_command"}.issubset(descriptors)
    assert descriptors["run_command"]["permission"] == "COMMAND_RESTRICTED"
    assert descriptors["run_command"]["input_schema"]["additionalProperties"] is False
    assert descriptors["read_file"]["recent_call_count"] == 0
    assert descriptors["apply_patch"]["enabled"] is False

    diagnostics = client.get("/api/v1/diagnostics", headers=auth_headers())
    assert diagnostics.status_code == 200
    diagnostic_body = diagnostics.json()
    assert diagnostic_body["operating_system"] in {"Darwin", "Linux", "Windows"}
    assert diagnostic_body["architecture"]
    assert diagnostic_body["database_type"] == "sqlite"
    assert diagnostic_body["sidecar_pid"] > 0
    assert diagnostic_body["telemetry_enabled"] is False
    serialized = diagnostics.text
    assert TOKEN not in serialized
    assert "api_key" not in serialized.casefold()


def test_pr_diff_review_map_and_tour_are_bound_to_real_git_and_index(
    client: TestClient,
    tmp_path: Path,
) -> None:
    repository_path = tmp_path / "review-workspace"
    repository_path.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repository_path, check=True)
    subprocess.run(
        ["git", "config", "user.email", "tracegate@example.invalid"],
        cwd=repository_path,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "TraceGate Test"],
        cwd=repository_path,
        check=True,
    )
    (repository_path / "main.py").write_text("def value():\n    return 1\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=repository_path, check=True)
    subprocess.run(["git", "commit", "-qm", "base"], cwd=repository_path, check=True)
    base_sha = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=repository_path, text=True
    ).strip()

    (repository_path / "helper.py").write_text(
        "def doubled(number):\n    return number * 2\n",
        encoding="utf-8",
    )
    (repository_path / "main.py").write_text(
        "from helper import doubled\n\ndef value():\n    return doubled(2)\n",
        encoding="utf-8",
    )
    subprocess.run(["git", "add", "."], cwd=repository_path, check=True)
    subprocess.run(["git", "commit", "-qm", "head"], cwd=repository_path, check=True)
    head_sha = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=repository_path, text=True
    ).strip()

    repository = client.post(
        "/api/v1/repositories",
        headers=auth_headers(),
        json={"full_name": "acme/review", "local_path": str(repository_path)},
    ).json()
    indexed = client.post(
        f"/api/v1/repositories/{repository['id']}/index",
        headers=auth_headers(),
    )
    assert indexed.status_code == 200
    assert indexed.json()["commit_sha"] == head_sha
    with client.app.state.database.session_factory() as session:
        pull_request = PullRequest(
            repository_id=repository["id"],
            number=4,
            title="Review graph",
            state="open",
            url="https://github.com/acme/review/pull/4",
            base_sha=base_sha,
            head_sha=head_sha,
            changed_files=2,
        )
        session.add(pull_request)
        session.commit()
        session.refresh(pull_request)
        pull_request_id = pull_request.id

    diff = client.get(
        f"/api/v1/pull-requests/{pull_request_id}/diff",
        headers=auth_headers(),
        params={"path": "main.py"},
    )
    assert diff.status_code == 200
    assert {item["path"] for item in diff.json()["changed_files"]} == {"helper.py", "main.py"}
    assert "return 1" in diff.json()["original"]
    assert "return doubled(2)" in diff.json()["modified"]

    review_map = client.get(
        f"/api/v1/pull-requests/{pull_request_id}/graph",
        headers=auth_headers(),
    )
    assert review_map.status_code == 200
    graph_body = review_map.json()
    assert graph_body["head_sha"] == head_sha
    assert graph_body["index_version"] == indexed.json()["id"]
    assert graph_body["source"] == "git_diff+static_index+agent_evidence"
    assert {node["path"] for node in graph_body["nodes"] if node["impact_depth"] == 0} >= {
        "helper.py",
        "main.py",
    }
    assert all(edge["confirmed"] for edge in graph_body["edges"])

    tour = client.get(
        f"/api/v1/pull-requests/{pull_request_id}/tour",
        headers=auth_headers(),
    )
    assert tour.status_code == 200
    assert {step["files"][0] for step in tour.json()["steps"]} == {"helper.py", "main.py"}
    assert all(step["confidence"] in {"high", "low"} for step in tour.json()["steps"])


def test_public_github_sync_persists_real_provider_shape(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeProvider:
        def __init__(self, token: str | None = None) -> None:
            assert token is None

        async def list_pull_requests(self, *_args: object, **_kwargs: object):  # type: ignore[no-untyped-def]
            pull = PullRequestData.model_validate(
                {
                    "number": 7,
                    "title": "Parser boundary",
                    "state": "open",
                    "html_url": "https://github.com/acme/synced/pull/7",
                    "updated_at": "2026-07-10T07:00:00Z",
                    "created_at": "2026-07-09T07:00:00Z",
                    "user": {"login": "octocat"},
                    "base": {"sha": "a" * 40},
                    "head": {"sha": "b" * 40},
                    "additions": 4,
                    "deletions": 1,
                    "changed_files": 1,
                }
            )
            return [pull], '"etag-7"', GitHubRateLimit(60, 59, None)

        async def close(self) -> None:
            return None

    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GH_TOKEN", raising=False)
    monkeypatch.setattr("tracegate.studio.github_sync.GitHubProvider", FakeProvider)
    created = client.post(
        "/api/v1/repositories",
        headers=auth_headers(),
        json={"full_name": "acme/synced"},
    ).json()

    synced = client.post(f"/api/v1/repositories/{created['id']}/sync", headers=auth_headers())
    assert synced.status_code == 200
    assert synced.json()["changed_pull_requests"] == 1
    assert synced.json()["github_rate_remaining"] == 59

    inbox = client.get("/api/v1/pull-requests", headers=auth_headers())
    assert inbox.status_code == 200
    assert inbox.json()["total"] == 1
    assert inbox.json()["items"][0]["head_sha"] == "b" * 40
    assert inbox.json()["items"][0]["analysis_status"] == "not_analyzed"


def test_github_webhook_requires_hmac_deduplicates_and_updates_enrolled_repository(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repository = client.post(
        "/api/v1/repositories",
        headers=auth_headers(),
        json={"full_name": "acme/webhook"},
    ).json()
    payload = {
        "repository": {"full_name": "acme/webhook"},
        "pull_request": {
            "number": 9,
            "title": "Webhook update",
            "state": "open",
            "html_url": "https://github.com/acme/webhook/pull/9",
            "draft": False,
            "updated_at": "2026-07-10T09:00:00Z",
            "created_at": "2026-07-10T08:00:00Z",
            "merged_at": None,
            "closed_at": None,
            "additions": 7,
            "deletions": 2,
            "changed_files": 1,
            "user": {"login": "octocat"},
            "base": {"sha": "a" * 40},
            "head": {"sha": "b" * 40},
        },
    }
    body = json.dumps(payload, separators=(",", ":")).encode()
    headers = {
        "X-GitHub-Delivery": "delivery-0001",
        "X-GitHub-Event": "pull_request",
        "X-Hub-Signature-256": "sha256=invalid",
        "Content-Type": "application/json",
    }
    monkeypatch.delenv("TRACEGATE_GITHUB_WEBHOOK_SECRET", raising=False)
    unavailable = client.post("/api/v1/webhooks/github", headers=headers, content=body)
    assert unavailable.status_code == 503
    assert unavailable.json()["error"]["message"] == "Webhook Relay 未配置"

    secret = "test-webhook-secret-not-for-production"
    monkeypatch.setenv("TRACEGATE_GITHUB_WEBHOOK_SECRET", secret)
    headers["X-Hub-Signature-256"] = "sha256=" + hmac.new(
        secret.encode(), body, hashlib.sha256
    ).hexdigest()
    accepted = client.post("/api/v1/webhooks/github", headers=headers, content=body)
    assert accepted.status_code == 200
    assert accepted.json() == {"accepted": True, "duplicate": False, "status": "processed"}
    duplicate = client.post("/api/v1/webhooks/github", headers=headers, content=body)
    assert duplicate.json() == {"accepted": True, "duplicate": True, "status": "processed"}

    inbox = client.get(
        "/api/v1/pull-requests",
        headers=auth_headers(),
        params={"repository_id": repository["id"]},
    ).json()
    assert inbox["total"] == 1
    assert inbox["items"][0]["head_sha"] == "b" * 40

    different = json.dumps({**payload, "action": "synchronize"}).encode()
    headers["X-Hub-Signature-256"] = "sha256=" + hmac.new(
        secret.encode(), different, hashlib.sha256
    ).hexdigest()
    mismatch = client.post("/api/v1/webhooks/github", headers=headers, content=different)
    assert mismatch.status_code == 409
    assert mismatch.json()["error"]["code"] == "webhook_delivery_mismatch"


def test_docs_and_unknown_routes_are_not_exposed(client: TestClient) -> None:
    for path in ("/docs", "/redoc", "/openapi.json", "/api/v1/unknown"):
        response = client.get(path, headers=auth_headers())
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "not_found"
