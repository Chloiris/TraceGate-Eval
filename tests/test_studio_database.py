from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import inspect, select

from tracegate.studio.app import create_app
from tracegate.studio.config import StudioSettings
from tracegate.studio.database import StudioDatabase
from tracegate.studio.migration_runner import (
    DatabaseMigrationError,
    current_revision,
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
            "onboarding_state",
            "pull_request_snapshots",
            "pull_requests",
            "repository_syncs",
            "repositories",
        } <= tables
        assert current_revision(database.engine) == "20260710_0003"
        with database.session_factory() as session:
            settings = session.scalar(select(AppSettings))
            onboarding = session.scalar(select(OnboardingState))
            assert settings is not None
            assert settings.theme == "system"
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
        assert current_revision(database.engine) == "20260710_0003"
    finally:
        database.dispose()


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
        assert current_revision(upgraded.engine) == "20260710_0003"
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
