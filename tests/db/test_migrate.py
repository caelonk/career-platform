from __future__ import annotations

import pytest
from sqlalchemy import create_engine, inspect

from app.db.migrate import alembic_config, current_revision, head_revision, upgrade_to_head
from tests.postgres_support import require_local_test_database


def test_alembic_config_round_trips_percent_encoded_passwords():
    url = "postgresql+psycopg://user:p%40ss%25word@localhost:5432/db"
    assert alembic_config(url).get_main_option("sqlalchemy.url") == url


def test_upgrade_to_head_on_sqlite(tmp_path):
    url = f"sqlite:///{tmp_path / 'm.db'}"
    assert current_revision(url) is None
    upgrade_to_head(url)
    assert current_revision(url) == head_revision() == "20240917_initial_schema"
    assert "projects" in inspect(create_engine(url)).get_table_names()


@pytest.mark.parametrize("host", ["localhost", "127.0.0.1"])
def test_local_test_database_is_allowed(host):
    assert require_local_test_database(f"postgresql://u:p@{host}:5432/d").startswith("postgresql+psycopg://")


def test_remote_test_database_is_refused():
    with pytest.raises(ValueError, match="local"):
        require_local_test_database("postgresql://u:p@monorail.proxy.rlwy.net:41234/railway")
