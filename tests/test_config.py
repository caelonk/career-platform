from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.config import DEFAULT_ADMIN_PASSWORD_HASH, Settings, normalize_database_url

PRIVATE_HASH = "pbkdf2_sha256$200000$c2FsdA==$ZGlnZXN0"


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


@pytest.mark.parametrize("secret", ["", "development-secret-key", "change-me-in-development"])
def test_production_rejects_public_secret_keys(secret):
    with pytest.raises(ValidationError, match="SECRET_KEY"):
        Settings(_env_file=None, environment="production", secret_key=secret, admin_password=PRIVATE_HASH)


def test_production_rejects_default_admin_password_hash():
    with pytest.raises(ValidationError, match="ADMIN_PASSWORD"):
        Settings(_env_file=None, environment="production", secret_key="a-private-value", admin_password=DEFAULT_ADMIN_PASSWORD_HASH)


def test_production_accepts_private_values():
    settings = Settings(_env_file=None, environment="production", secret_key="a-private-value", admin_password=PRIVATE_HASH)
    assert settings.environment == "production"


def test_development_allows_defaults():
    assert Settings(_env_file=None, environment="development").secret_key == "development-secret-key"


@pytest.mark.parametrize("environment", ["Production", "PRODUCTION", " production "])
def test_production_guard_ignores_case_and_whitespace(environment):
    with pytest.raises(ValidationError, match="SECRET_KEY"):
        Settings(_env_file=None, environment=environment)


def test_railway_enforces_guard_when_environment_is_not_set(monkeypatch):
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    monkeypatch.setenv("RAILWAY_ENVIRONMENT_NAME", "production")
    with pytest.raises(ValidationError, match="SECRET_KEY"):
        Settings(_env_file=None)


def test_railway_counts_as_production_with_private_values(monkeypatch):
    monkeypatch.setenv("RAILWAY_ENVIRONMENT_NAME", "production")
    settings = Settings(_env_file=None, environment="development", secret_key="a-private-value", admin_password=PRIVATE_HASH)
    assert settings.is_production is True


def test_local_development_is_not_production(monkeypatch):
    monkeypatch.delenv("RAILWAY_ENVIRONMENT_NAME", raising=False)
    assert Settings(_env_file=None, environment="development").is_production is False
