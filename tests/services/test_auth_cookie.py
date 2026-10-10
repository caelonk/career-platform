from __future__ import annotations

from fastapi import Response

from app.config import Settings
from app.services import auth

PRIVATE_HASH = "pbkdf2_sha256$200000$c2FsdA==$ZGlnZXN0"


def _cookie_header(monkeypatch, settings: Settings) -> str:
    monkeypatch.setattr(auth, "get_settings", lambda: settings)
    response = Response()
    auth.write_admin_cookie(response)
    return response.headers["set-cookie"]


def test_admin_cookie_is_secure_on_railway_without_environment_variable(monkeypatch):
    monkeypatch.setenv("RAILWAY_ENVIRONMENT_NAME", "production")
    settings = Settings(_env_file=None, environment="development", secret_key="a-private-value", admin_password=PRIVATE_HASH)
    assert "Secure" in _cookie_header(monkeypatch, settings)


def test_admin_cookie_is_not_secure_in_local_development(monkeypatch):
    monkeypatch.delenv("RAILWAY_ENVIRONMENT_NAME", raising=False)
    assert "Secure" not in _cookie_header(monkeypatch, Settings(_env_file=None, environment="development"))
