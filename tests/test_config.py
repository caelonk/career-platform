from __future__ import annotations

import pytest

from app.config import Settings, normalize_database_url


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("postgresql://u:p@db.internal:5432/railway", "postgresql+psycopg://u:p@db.internal:5432/railway"),
        ("postgres://u:p@db.internal:5432/railway", "postgresql+psycopg://u:p@db.internal:5432/railway"),
        ("postgresql+psycopg://u:p@h/d", "postgresql+psycopg://u:p@h/d"),
        ("sqlite:///./career_platform.db", "sqlite:///./career_platform.db"),
    ],
)
def test_normalize_database_url(raw, expected):
    assert normalize_database_url(raw) == expected


def test_settings_normalize_database_url():
    settings = Settings(_env_file=None, database_url="postgresql://u:p@h:5432/d")
    assert settings.database_url == "postgresql+psycopg://u:p@h:5432/d"
