from __future__ import annotations

from io import StringIO
from pathlib import Path

import pytest
from alembic import command
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import inspect, select

from tracegate.studio.app import create_app
from tracegate.studio.config import StudioSettings
from tracegate.studio.database import StudioDatabase
from tracegate.studio.migration_runner import (
    DatabaseMigrationError,
    current_revision,
    migration_config,
    upgrade_database,
)
from tracegate.studio.models import AppSettings, OnboardingState


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
            "pull_request_snapshots",
            "pull_requests",
            "repository_syncs",
            "repositories",
        } <= tables
        assert current_revision(database.engine) == "20260710_0004"
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
            assert onboarding is not None
            assert onboarding.current_step == "welcome"
    finally:
        database.dispose()


def test_migration_is_idempotent(tmp_path: Path) -> None:
    url = database_url(tmp_path)
    upgrade_database(url)
    upgrade_database(url)
    database = StudioDatabase(url)
    try:
        assert current_revision(database.engine) == "20260710_0004"
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


def test_agent_index_migration_upgrades_existing_p0_database_without_data_loss(tmp_path: Path) -> None:
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
        assert current_revision(upgraded.engine) == "20260710_0004"
        with upgraded.engine.connect() as connection:
            assert connection.exec_driver_sql(
                "SELECT full_name FROM repositories WHERE id = 'repo-1'"
            ).scalar_one() == "acme/widget"
            assert "indexed_content_fts" in inspect(upgraded.engine).get_table_names()
    finally:
        upgraded.dispose()


def test_app_without_migration_fails_instead_of_creating_fallback_schema(tmp_path: Path) -> None:
    settings = StudioSettings(
        local_api_token=SecretStr(TOKEN),
        database_url=database_url(tmp_path, "unmigrated.db"),
        auto_migrate=False,
        eval_root=tmp_path,
    )
    with pytest.raises(DatabaseMigrationError, match="unversioned"):
        with TestClient(create_app(settings)):
            pass
