from __future__ import annotations

from pathlib import Path
from typing import Any

from tracegate.studio.database import StudioDatabase
from tracegate.studio.migration_runner import upgrade_database
from tracegate.studio.models import AgentRun, AppSettings, ModelProfile, PullRequest, Repository
from tracegate.studio.run_manager import RunManager, configured_model


def test_configured_model_uses_every_persisted_runtime_parameter(
    tmp_path: Path,
    monkeypatch,
) -> None:  # type: ignore[no-untyped-def]
    url = f"sqlite+pysqlite:///{(tmp_path / 'model.db').as_posix()}"
    upgrade_database(url)
    database = StudioDatabase(url)
    captured: dict[str, Any] = {}

    class CapturingProvider:
        def __init__(self, **kwargs: Any) -> None:
            captured.update(kwargs)

    monkeypatch.setenv("TRACEGATE_LLM_API_KEY", "real-test-key-kept-out-of-persistence")
    monkeypatch.setattr("tracegate.studio.run_manager.OpenAICompatibleProvider", CapturingProvider)
    try:
        with database.session_factory() as session:
            settings = session.get(AppSettings, 1)
            assert settings is not None
            settings.model_provider = "deepseek"
            settings.model_name = "deepseek-chat"
            settings.model_temperature = 0.4
            settings.model_max_output_tokens = 6144
            settings.model_timeout_seconds = 75
            settings.model_max_retries = 1
            settings.model_native_structured_output = True
            settings.model_streaming_enabled = True
            settings.model_native_tool_calling = True
            session.commit()
            configured_model(session)

        assert captured["base_url"] == "https://api.deepseek.com"
        assert captured["model"] == "deepseek-chat"
        assert captured["temperature"] == 0.4
        assert captured["max_tokens"] == 6144
        assert captured["timeout_seconds"] == 75
        assert captured["max_retries"] == 1
        assert captured["native_structured_output"] is True
        assert captured["streaming_enabled"] is True
        assert captured["native_tool_calling"] is True
        assert captured["api_key"].get_secret_value() == "real-test-key-kept-out-of-persistence"
    finally:
        database.dispose()


def test_automatic_analysis_queues_only_matching_index_and_deduplicates(
    tmp_path: Path,
    monkeypatch,
) -> None:  # type: ignore[no-untyped-def]
    url = f"sqlite+pysqlite:///{(tmp_path / 'automatic.db').as_posix()}"
    upgrade_database(url)
    database = StudioDatabase(url)
    head_sha = "b" * 40
    with database.session_factory() as session:
        settings = session.get(AppSettings, 1)
        assert settings is not None
        settings.automatic_analysis_enabled = True
        settings.automatic_analysis_require_checks_success = True
        settings.model_provider = "deepseek"
        settings.model_name = "deepseek-chat"
        settings.model_temperature = 0.25
        repository = Repository(
            owner="acme",
            name="widget",
            full_name="acme/widget",
            monitoring_enabled=True,
            current_commit_sha=head_sha,
            current_index_version="index-version-1",
        )
        session.add(repository)
        session.flush()
        pull_request = PullRequest(
            repository_id=repository.id,
            number=9,
            title="Ready for automatic review",
            state="open",
            url="https://github.com/acme/widget/pull/9",
            head_sha=head_sha,
            checks_status="success",
        )
        session.add(pull_request)
        session.commit()
        repository_id = repository.id
        pull_request_id = pull_request.id

    class FakeModel:
        profile = "openai-compatible:test-model:json-compatibility"

    monkeypatch.setattr("tracegate.studio.run_manager.configured_model", lambda _session: FakeModel())
    manager = RunManager(database.session_factory)
    started: list[str] = []
    monkeypatch.setattr(manager, "start", lambda run_id, _model: started.append(run_id))
    try:
        first = manager.enqueue_automatic(repository_id)
        second = manager.enqueue_automatic(repository_id)
        assert first.started == 1
        assert first.skipped_reason is None
        assert second.started == 0
        assert len(started) == 1
        with database.session_factory() as session:
            run = session.query(AgentRun).filter_by(pull_request_id=pull_request_id).one()
            assert run.status == "queued"
            assert run.head_sha == head_sha
            assert run.model_profile_id is not None
            profile = session.get(ModelProfile, run.model_profile_id)
            assert profile is not None
            assert profile.provider == "deepseek"
            assert profile.base_url == "https://api.deepseek.com"
            assert profile.model_name == "deepseek-chat"
            assert profile.temperature == 0.25
            assert "api_key" not in profile.__table__.columns
            assert "credential" not in profile.__table__.columns
            pull_request = session.get(PullRequest, pull_request_id)
            assert pull_request is not None
            assert pull_request.analysis_status == "queued"
    finally:
        database.dispose()
