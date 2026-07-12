from __future__ import annotations

from io import StringIO
from pathlib import Path
from datetime import datetime, timedelta, timezone

import pytest
from alembic import command
from fastapi.testclient import TestClient
from pydantic import SecretStr, ValidationError
from sqlalchemy import func, inspect, select
from sqlalchemy.exc import IntegrityError

from tracegate.studio.app import create_app
from tracegate.studio.config import StudioSettings
from tracegate.studio.database import StudioDatabase
from tracegate.studio.migration_runner import (
    DatabaseMigrationError,
    current_revision,
    migration_config,
    upgrade_database,
)
from tracegate.studio.models import (
    AgentRun,
    AppSettings,
    Finding,
    FixConfirmation,
    FixEvent,
    FixResult,
    FixSession,
    FixStep,
    FixToolCallRecord,
    IndexVersion,
    OnboardingState,
    PatchProposalRecord,
    PullRequest,
    Repository,
    ValidationRun,
)
from tracegate.studio.schemas import SettingsUpdate


TOKEN = "database-test-token-0123456789-abcdef"


def database_url(tmp_path: Path, name: str = "studio.db") -> str:
    return f"sqlite+pysqlite:///{(tmp_path / name).as_posix()}"


def test_initial_migration_creates_core_tables_and_singletons(tmp_path: Path) -> None:
    url = database_url(tmp_path)
    upgrade_database(url)
    database = StudioDatabase(url)
    try:
        tables = set(inspect(database.engine).get_table_names())
        assert {
            "agent_runs",
            "alembic_version",
            "app_settings",
            "check_runs",
            "changed_files",
            "changed_hunks",
            "commits",
            "eval_runs",
            "evidence_records",
            "fix_confirmations",
            "fix_events",
            "fix_results",
            "fix_sessions",
            "fix_steps",
            "fix_tool_calls",
            "findings",
            "index_versions",
            "webhook_deliveries",
            "indexed_files",
            "indexed_symbols",
            "indexed_content_fts",
            "agent_steps",
            "tool_calls",
            "graph_nodes",
            "graph_edges",
            "memory_claims",
            "model_profiles",
            "notification_records",
            "onboarding_state",
            "patch_proposals",
            "pull_request_snapshots",
            "pull_requests",
            "repository_syncs",
            "repositories",
            "validation_runs",
        } <= tables
        assert current_revision(database.engine) == "20260712_0006"
        indexed_file_columns = {
            column["name"]
            for column in inspect(database.engine).get_columns("indexed_files")
        }
        assert {"exports_json", "relationships_json"} <= indexed_file_columns
        with database.session_factory() as session:
            settings = session.scalar(select(AppSettings))
            onboarding = session.scalar(select(OnboardingState))
            assert settings is not None
            assert settings.theme == "system"
            assert settings.close_notice_dismissed is False
            assert settings.notifications_enabled is True
            assert settings.model_temperature == 0.0
            assert settings.model_max_output_tokens == 4096
            assert settings.model_timeout_seconds == 60
            assert settings.model_max_retries == 2
            assert settings.model_native_structured_output is False
            assert settings.model_streaming_enabled is False
            assert settings.model_native_tool_calling is False
            assert settings.model_context_scope == "changed_files"
            assert settings.model_input_cost_per_million == 0.0
            assert settings.model_output_cost_per_million == 0.0
            assert settings.github_poll_interval_seconds == 60
            assert settings.automatic_analysis_enabled is False
            assert settings.automatic_analysis_include_drafts is False
            assert settings.automatic_analysis_require_checks_success is False
            assert settings.analysis_paused is False
            assert settings.webhook_relay_url is None
            assert settings.webhook_relay_device_id is None
            assert settings.disabled_agents_json == []
            assert settings.disabled_tools_json == []
            assert settings.autofix_max_files == 8
            assert settings.autofix_max_changed_lines == 800
            assert settings.autofix_confirmation_ttl_seconds == 900
            assert settings.autofix_workspace_retention_hours == 24
            assert onboarding is not None
            assert onboarding.current_step == "welcome"

        fix_session_foreign_keys = {
            tuple(item["constrained_columns"]): (
                item["referred_table"],
                tuple(item["referred_columns"]),
                item["options"].get("ondelete"),
            )
            for item in inspect(database.engine).get_foreign_keys("fix_sessions")
        }
        assert fix_session_foreign_keys == {
            ("repository_id",): ("repositories", ("id",), "CASCADE"),
            ("pull_request_id",): ("pull_requests", ("id",), "CASCADE"),
            ("finding_id",): ("findings", ("id",), "CASCADE"),
            ("source_agent_run_id",): ("agent_runs", ("id",), "CASCADE"),
            ("index_version_id",): ("index_versions", ("id",), "SET NULL"),
            ("workspace_index_version_id",): ("index_versions", ("id",), "SET NULL"),
        }
        assert {
            item["name"]
            for item in inspect(database.engine).get_check_constraints("fix_sessions")
        } >= {
            "ck_fix_sessions_status",
            "ck_fix_sessions_permission_mode",
            "ck_fix_sessions_eligibility_status",
            "ck_fix_sessions_cleanup_status",
            "ck_fix_sessions_lock_version",
            "ck_fix_sessions_usage_nonnegative",
            "ck_fix_sessions_sha_lengths",
        }
        assert {
            item["name"]
            for item in inspect(database.engine).get_unique_constraints(
                "patch_proposals"
            )
        } >= {
            "uq_patch_proposals_session_version",
            "uq_patch_proposals_session_hash",
        }
        confirmation_foreign_keys = {
            tuple(item["constrained_columns"]): item["referred_table"]
            for item in inspect(database.engine).get_foreign_keys("fix_confirmations")
        }
        assert confirmation_foreign_keys == {
            (
                "fix_session_id",
                "repository_id",
                "pull_request_id",
                "finding_id",
                "head_sha",
            ): "fix_sessions",
            ("repository_id",): "repositories",
            ("pull_request_id",): "pull_requests",
            ("finding_id",): "findings",
        }
    finally:
        database.dispose()


def test_migration_is_idempotent(tmp_path: Path) -> None:
    url = database_url(tmp_path)
    upgrade_database(url)
    upgrade_database(url)
    database = StudioDatabase(url)
    try:
        assert current_revision(database.engine) == "20260712_0006"
    finally:
        database.dispose()


def test_mysql_offline_ddl_does_not_autoincrement_singleton_ids() -> None:
    output = StringIO()
    config = migration_config("mysql+pymysql://tracegate:unused@127.0.0.1/tracegate")
    config.output_buffer = output

    command.upgrade(config, "head", sql=True)

    ddl = output.getvalue()
    assert "id INTEGER NOT NULL AUTO_INCREMENT" not in ddl
    assert "CONSTRAINT ck_app_settings_singleton CHECK (id = 1)" in ddl
    assert "CONSTRAINT ck_onboarding_state_singleton CHECK (id = 1)" in ddl
    assert "CREATE TABLE fix_sessions" in ddl
    assert "CREATE TABLE patch_proposals" in ddl
    assert "CREATE TABLE fix_confirmations" in ddl
    assert "CREATE TABLE validation_runs" in ddl
    assert "CREATE TABLE fix_results" in ddl
    assert "CREATE TABLE fix_steps" in ddl
    assert "CREATE TABLE fix_tool_calls" in ddl
    assert "CREATE TABLE fix_events" in ddl
    assert "CONSTRAINT ck_fix_sessions_status CHECK" in ddl
    assert "CONSTRAINT uq_fix_confirmations_nonce_hash UNIQUE (nonce_hash)" in ddl
    assert "autofix_max_files INTEGER NOT NULL DEFAULT '8'" in ddl
    indexed_files_ddl = ddl.split("CREATE TABLE indexed_files", 1)[1].split(";", 1)[0]
    assert "path VARCHAR(512) NOT NULL" in indexed_files_ddl
    changed_files_ddl = ddl.split("CREATE TABLE changed_files", 1)[1].split(";", 1)[0]
    assert "path VARCHAR(512) NOT NULL" in changed_files_ddl


def test_agent_index_migration_upgrades_existing_p0_database_without_data_loss(
    tmp_path: Path,
) -> None:
    url = database_url(tmp_path)
    upgrade_database(url, "20260710_0001")
    database = StudioDatabase(url)
    try:
        with database.engine.begin() as connection:
            connection.exec_driver_sql(
                "INSERT INTO repositories "
                "(id, owner, name, full_name, monitoring_enabled, connection_status) "
                "VALUES ('repo-1', 'acme', 'widget', 'acme/widget', 0, 'not_connected')"
            )
    finally:
        database.dispose()

    upgrade_database(url)
    upgraded = StudioDatabase(url)
    try:
        assert current_revision(upgraded.engine) == "20260712_0006"
        with upgraded.engine.connect() as connection:
            assert (
                connection.exec_driver_sql(
                    "SELECT full_name FROM repositories WHERE id = 'repo-1'"
                ).scalar_one()
                == "acme/widget"
            )
            assert "indexed_content_fts" in inspect(upgraded.engine).get_table_names()
    finally:
        upgraded.dispose()


def test_autofix_migration_upgrades_existing_0005_database_without_data_loss(
    tmp_path: Path,
) -> None:
    url = database_url(tmp_path)
    upgrade_database(url, "20260711_0005")
    database = StudioDatabase(url)
    try:
        with database.engine.begin() as connection:
            connection.exec_driver_sql(
                "UPDATE app_settings SET language = 'en-US', model_name = 'existing-model' "
                "WHERE id = 1"
            )
    finally:
        database.dispose()

    upgrade_database(url)
    upgraded = StudioDatabase(url)
    try:
        assert current_revision(upgraded.engine) == "20260712_0006"
        with upgraded.session_factory() as session:
            settings = session.get(AppSettings, 1)
            assert settings is not None
            assert settings.language == "en-US"
            assert settings.model_name == "existing-model"
            assert settings.autofix_max_files == 8
            assert settings.autofix_max_changed_lines == 800
            assert settings.autofix_confirmation_ttl_seconds == 900
            assert settings.autofix_workspace_retention_hours == 24
        assert {
            "fix_sessions",
            "patch_proposals",
            "fix_confirmations",
            "validation_runs",
            "fix_results",
            "fix_steps",
            "fix_tool_calls",
            "fix_events",
        } <= set(inspect(upgraded.engine).get_table_names())
    finally:
        upgraded.dispose()


@pytest.mark.parametrize(
    "payload",
    [
        {"autofix_max_files": 0},
        {"autofix_max_files": 33},
        {"autofix_max_changed_lines": 49},
        {"autofix_max_changed_lines": 5001},
        {"autofix_confirmation_ttl_seconds": 59},
        {"autofix_confirmation_ttl_seconds": 3601},
        {"autofix_workspace_retention_hours": 0},
        {"autofix_workspace_retention_hours": 169},
    ],
)
def test_autofix_settings_schema_rejects_disabled_or_unbounded_limits(
    payload: dict[str, int],
) -> None:
    with pytest.raises(ValidationError):
        SettingsUpdate.model_validate(payload)


def test_autofix_records_enforce_uniqueness_and_cascade_from_repository(
    tmp_path: Path,
) -> None:
    url = database_url(tmp_path)
    upgrade_database(url)
    database = StudioDatabase(url)
    now = datetime.now(timezone.utc)
    try:
        with database.session_factory() as session:
            repository = Repository(
                id="repo-autofix",
                owner="acme",
                name="widget",
                full_name="acme/autofix-widget",
            )
            session.add(repository)
            session.flush()
            pull_request = PullRequest(
                id="pr-autofix",
                repository_id=repository.id,
                number=7,
                title="Autofix persistence",
                state="open",
                url="https://github.com/acme/widget/pull/7",
                base_sha="a" * 40,
                head_sha="b" * 40,
            )
            index_version = IndexVersion(
                id="index-autofix",
                repository_id=repository.id,
                commit_sha="b" * 40,
                status="ready",
                file_count=1,
                symbol_count=1,
                changed_count=1,
                deleted_count=0,
                duration_ms=1,
            )
            session.add_all([pull_request, index_version])
            session.flush()
            agent_run = AgentRun(
                id="run-autofix",
                repository_id=repository.id,
                pull_request_id=pull_request.id,
                status="completed",
                head_sha="b" * 40,
                index_version=index_version.id,
            )
            session.add(agent_run)
            session.flush()
            finding = Finding(
                id="finding-autofix",
                agent_run_id=agent_run.id,
                severity="medium",
                title="Persist a controlled fix",
                message="The finding is bound to the test Head SHA.",
            )
            session.add(finding)
            session.flush()
            fix_session = FixSession(
                id="fix-autofix",
                repository_id=repository.id,
                pull_request_id=pull_request.id,
                finding_id=finding.id,
                source_agent_run_id=agent_run.id,
                base_sha="a" * 40,
                head_sha="b" * 40,
                index_version_id=index_version.id,
            )
            session.add(fix_session)
            session.flush()
            patch = PatchProposalRecord(
                id="proposal-autofix",
                fix_session_id=fix_session.id,
                proposal_version=1,
                base_sha="a" * 40,
                head_sha="b" * 40,
                patch="--- a/main.py\n+++ b/main.py\n",
                patch_hash="c" * 64,
                rationale="Apply the bounded correction.",
                changed_files_json=["main.py"],
                changed_lines=1,
                confidence=0.9,
            )
            confirmation = FixConfirmation(
                id="confirmation-autofix",
                fix_session_id=fix_session.id,
                repository_id=repository.id,
                pull_request_id=pull_request.id,
                finding_id=finding.id,
                head_sha="b" * 40,
                patch_hash=patch.patch_hash,
                nonce_hash="d" * 64,
                expires_at=now + timedelta(minutes=15),
                confirmed_at=now,
            )
            validation = ValidationRun(
                id="validation-autofix",
                fix_session_id=fix_session.id,
                sequence=1,
                command=["git", "diff", "--check"],
                purpose="Reject whitespace errors.",
            )
            result = FixResult(
                id="result-autofix",
                fix_session_id=fix_session.id,
                resolution="NEEDS_HUMAN_REVIEW",
                validation_status="NO_TEST_COMMAND_AVAILABLE",
                re_review_status="INSUFFICIENT_STATIC_EVIDENCE",
            )
            step = FixStep(
                id="step-autofix",
                fix_session_id=fix_session.id,
                sequence=1,
                node="LOAD_FINDING",
            )
            session.add(step)
            session.flush()
            tool_call = FixToolCallRecord(
                id="tool-autofix",
                fix_step_id=step.id,
                tool_name="read_file",
                permission="REPOSITORY_READ",
                arguments_summary='{"path":"main.py"}',
                status="COMPLETED",
            )
            event = FixEvent(
                id="event-autofix",
                fix_session_id=fix_session.id,
                sequence=1,
                event_type="fix_session.created",
            )
            session.add_all(
                [
                    patch,
                    confirmation,
                    validation,
                    result,
                    tool_call,
                    event,
                ]
            )
            session.commit()

            session.add(
                FixConfirmation(
                    fix_session_id=fix_session.id,
                    repository_id=repository.id,
                    pull_request_id=pull_request.id,
                    finding_id=finding.id,
                    head_sha="e" * 40,
                    patch_hash="f" * 64,
                    nonce_hash="0" * 64,
                    expires_at=now + timedelta(minutes=15),
                )
            )
            with pytest.raises(IntegrityError):
                session.commit()
            session.rollback()

            session.add(
                FixEvent(
                    fix_session_id=fix_session.id,
                    sequence=1,
                    event_type="duplicate.sequence",
                )
            )
            with pytest.raises(IntegrityError):
                session.commit()
            session.rollback()

            session.delete(repository)
            session.commit()
            assert session.scalar(select(func.count()).select_from(FixSession)) == 0
            assert (
                session.scalar(select(func.count()).select_from(FixToolCallRecord)) == 0
            )
    finally:
        database.dispose()


def test_app_without_migration_fails_instead_of_creating_fallback_schema(
    tmp_path: Path,
) -> None:
    settings = StudioSettings(
        local_api_token=SecretStr(TOKEN),
        database_url=database_url(tmp_path, "unmigrated.db"),
        auto_migrate=False,
        eval_root=tmp_path,
    )
    with pytest.raises(DatabaseMigrationError, match="unversioned"):
        with TestClient(create_app(settings)):
            pass
