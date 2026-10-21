from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from app.db.session import engine_options


def test_sqlite_engine_options_keep_single_connection():
    options = engine_options("sqlite:///./x.db")
    assert options["poolclass"] is StaticPool
    assert options["connect_args"] == {"check_same_thread": False}


def test_postgres_engine_options_ping_before_use():
    assert engine_options("postgresql+psycopg://u:p@h/d")["pool_pre_ping"] is True


def test_postgres_connections_give_up_quickly_when_database_is_unreachable():
    # Without a timeout, a database that stops answering holds the request open
    # indefinitely, so the page never gets to return 503.
    assert engine_options("postgresql+psycopg://u:p@h/d")["connect_args"] == {"connect_timeout": 3}


def test_psycopg_dialect_is_installed():
    engine = create_engine("postgresql+psycopg://u:p@localhost/d", **engine_options("postgresql+psycopg://u:p@localhost/d"))
    assert engine.dialect.driver == "psycopg"
