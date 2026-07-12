from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from tracegate.config import PROJECT_ROOT
from tracegate.github import GitHubRateLimit
from tracegate.models import ModelConfigurationError
from tracegate.studio.app import create_app
from tracegate.studio.config import StudioSettings
from tracegate.studio.run_manager import configured_model


LOCAL_TOKEN = "runtime-test-local-token-0123456789abcdef"
CONTROL_TOKEN = "runtime-test-control-token-0123456789abcdef"
CONTROL_PATH = "/internal/v1/credentials"


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def runtime_client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    for name in (
        "GITHUB_TOKEN",
        "GH_TOKEN",
        "TRACEGATE_LLM_API_KEY",
        "DEEPSEEK_API_KEY",
        "TRACEGATE_RELAY_DEVICE_TOKEN",
    ):
        monkeypatch.delenv(name, raising=False)
    settings = StudioSettings(
        local_api_token=SecretStr(LOCAL_TOKEN),
        credential_control_token=SecretStr(CONTROL_TOKEN),
        database_url=f"sqlite+pysqlite:///{(tmp_path / 'studio.db').as_posix()}",
        eval_root=PROJECT_ROOT,
    )
    with TestClient(create_app(settings)) as client:
        yield client


def test_public_api_token_cannot_mutate_runtime_credentials(runtime_client: TestClient) -> None:
    credential_material = "not-a-real-runtime-credential-12345"
    response = runtime_client.put(
        f"{CONTROL_PATH}/github",
        headers=_headers(LOCAL_TOKEN),
        json={"secret": credential_material},
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"
    assert credential_material not in response.text


def test_github_credential_is_live_for_status_and_connection_probe(
    runtime_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    credential_material = "not-a-real-github-runtime-credential-12345"

    class FakeGitHubProvider:
        def __init__(self, token: str) -> None:
            assert token == credential_material

        async def test_authenticated_connection(self):  # type: ignore[no-untyped-def]
            return "runtime-user", GitHubRateLimit(5000, 4999, None)

        async def close(self) -> None:
            return None

    monkeypatch.setattr("tracegate.studio.api.GitHubProvider", FakeGitHubProvider)
    update = runtime_client.put(
        f"{CONTROL_PATH}/github",
        headers=_headers(CONTROL_TOKEN),
        json={"secret": credential_material},
    )
    assert update.status_code == 200
    assert update.json() == {"kind": "github", "configured": True}
    assert credential_material not in update.text

    system_status = runtime_client.get("/api/v1/system/status", headers=_headers(LOCAL_TOKEN))
    assert system_status.json()["components"]["github"]["state"] == "ready"
    probe = runtime_client.post(
        "/api/v1/connections/test",
        headers=_headers(LOCAL_TOKEN),
        json={"component": "github"},
    )
    assert probe.status_code == 200
    assert probe.json()["message"] == "GitHub authenticated as runtime-user."
    assert credential_material not in probe.text

    deleted = runtime_client.delete(
        f"{CONTROL_PATH}/github",
        headers=_headers(CONTROL_TOKEN),
    )
    assert deleted.json() == {"kind": "github", "configured": False}
    missing_probe = runtime_client.post(
        "/api/v1/connections/test",
        headers=_headers(LOCAL_TOKEN),
        json={"component": "github"},
    )
    assert missing_probe.status_code == 409
    assert missing_probe.json()["error"]["code"] == "github_not_configured"


def test_model_credential_is_live_for_the_real_provider_factory(
    runtime_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    credential_material = "not-a-real-model-runtime-credential-12345"
    captured: dict[str, bool] = {}

    class FakeProvider:
        profile = "openai-compatible:test-model:json-compatibility"

        def __init__(self, *, api_key: SecretStr, **_kwargs: object) -> None:
            captured["configured"] = bool(api_key.get_secret_value())

        async def complete_structured(self, **_kwargs: object):  # type: ignore[no-untyped-def]
            return SimpleNamespace(provider_mode="compatibility_json", input_tokens=2, output_tokens=1)

    monkeypatch.setattr("tracegate.studio.run_manager.OpenAICompatibleProvider", FakeProvider)
    settings_response = runtime_client.put(
        "/api/v1/settings",
        headers=_headers(LOCAL_TOKEN),
        json={
            "model_provider": "deepseek",
            "model_name": "deepseek-chat",
        },
    )
    assert settings_response.status_code == 200

    update = runtime_client.put(
        f"{CONTROL_PATH}/model",
        headers=_headers(CONTROL_TOKEN),
        json={"secret": credential_material},
    )
    assert update.json() == {"kind": "model", "configured": True}
    assert credential_material not in update.text
    with runtime_client.app.state.database.session_factory() as session:
        model = configured_model(session)
    assert isinstance(model, FakeProvider)
    assert captured == {"configured": True}

    deleted = runtime_client.delete(
        f"{CONTROL_PATH}/model",
        headers=_headers(CONTROL_TOKEN),
    )
    assert deleted.json() == {"kind": "model", "configured": False}
    with runtime_client.app.state.database.session_factory() as session:
        with pytest.raises(ModelConfigurationError, match="credential is not configured"):
            configured_model(session)
