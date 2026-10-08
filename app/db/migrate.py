from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine

from app.config import normalize_database_url

REPO_ROOT = Path(__file__).resolve().parents[2]


def alembic_config(database_url: str) -> Config:
    """Alembic config for this repo, pointed at database_url instead of the settings URL."""
    config = Config(str(REPO_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(REPO_ROOT / "migrations"))
    # Config values go through ConfigParser interpolation, so a literal % (URL-encoded passwords) must be doubled.
    config.set_main_option("sqlalchemy.url", normalize_database_url(database_url).replace("%", "%%"))
    config.attributes["database_url"] = normalize_database_url(database_url)
    return config


def upgrade_to_head(database_url: str) -> None:
    command.upgrade(alembic_config(database_url), "head")


def head_revision() -> str:
    return ScriptDirectory.from_config(alembic_config("sqlite://")).get_current_head()


def current_revision(database_url: str) -> str | None:
    engine = create_engine(normalize_database_url(database_url))
    try:
        with engine.connect() as connection:
            return MigrationContext.configure(connection).get_current_revision()
    finally:
        engine.dispose()
