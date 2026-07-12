from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import Engine


MIGRATIONS_DIR = Path(__file__).resolve().parent / "migrations"


class DatabaseMigrationError(RuntimeError):
    """Raised when the Studio database is not at the required schema revision."""


def migration_config(database_url: str) -> Config:
    config = Config()
    config.set_main_option("script_location", MIGRATIONS_DIR.as_posix())
    config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))
    return config


def upgrade_database(database_url: str, revision: str = "head") -> None:
    command.upgrade(migration_config(database_url), revision)


def current_revision(engine: Engine) -> str | None:
    with engine.connect() as connection:
        return MigrationContext.configure(connection).get_current_revision()


def require_current_revision(engine: Engine, database_url: str) -> str:
    config = migration_config(database_url)
    heads = set(ScriptDirectory.from_config(config).get_heads())
    current = current_revision(engine)
    if current is None or current not in heads:
        expected = ", ".join(sorted(heads)) or "<missing migration head>"
        raise DatabaseMigrationError(
            f"database revision is {current or '<unversioned>'}; expected {expected}"
        )
    return current
