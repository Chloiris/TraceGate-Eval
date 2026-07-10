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
            "onboarding_state",
            "pull_requests",
            "repositories",
        } <= tables
        assert current_revision(database.engine) == "20260710_0001"
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
        assert current_revision(database.engine) == "20260710_0001"
    finally:
        database.dispose()


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
