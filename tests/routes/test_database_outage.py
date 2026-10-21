"""What visitors see when the database can't be reached, and after it comes back."""

from __future__ import annotations

import json

import pytest
from sqlalchemy.exc import OperationalError

from app.config import get_settings

SNAPSHOT_MARKER = "OLD-SNAPSHOT-CONTENT"


class _BrokenSession:
    """Stands in for a session whose database connection fails, as a stopped database would."""

    def execute(self, *args, **kwargs):
        raise OperationalError("SELECT 1", {}, Exception("connection refused"))

    def close(self):
        pass


@pytest.fixture
def snapshot_dir(tmp_path, monkeypatch):
    directory = tmp_path / "snapshots"
    directory.mkdir()
    (directory / "home.html").write_text(f"<html><body>{SNAPSHOT_MARKER}</body></html>", encoding="utf-8")
    monkeypatch.setenv("SNAPSHOT_DIR", str(directory))
    get_settings.cache_clear()
    monkeypatch.setattr("app.services.profile_fallback._last_known", None)
    yield directory
    get_settings.cache_clear()


def _break_database(monkeypatch):
    monkeypatch.setattr("app.routes.public.SessionLocal", lambda: _BrokenSession())


def _restore_database(monkeypatch):
    monkeypatch.setattr("app.routes.public.SessionLocal", None)


def test_healthy_home_returns_200_with_projects(client, snapshot_dir):
    response = client.get("/")
    assert response.status_code == 200
    assert "Featured project" in response.text
    assert "Projects temporarily unavailable" not in response.text


def test_database_failure_returns_503_with_message(client, snapshot_dir, monkeypatch):
    _break_database(monkeypatch)
    response = client.get("/", headers={"accept": "text/html"})
    assert response.status_code == 503
    assert "Projects temporarily unavailable" in response.text


def test_database_failure_does_not_serve_the_old_snapshot(client, snapshot_dir, monkeypatch):
    _break_database(monkeypatch)
    response = client.get("/")
    assert SNAPSHOT_MARKER not in response.text
    assert "Featured project" not in response.text


def test_database_failure_keeps_profile_seen_on_an_earlier_request(client, snapshot_dir, monkeypatch):
    assert client.get("/").status_code == 200
    _break_database(monkeypatch)
    response = client.get("/")
    assert response.status_code == 503
    assert "Alex Jordan" in response.text


def test_database_failure_after_a_restart_reads_profile_from_saved_file(client, snapshot_dir, monkeypatch):
    profile = {"name": "Alex Jordan", "headline": "Business Transformation Leader", "summary": "Saved summary."}
    (snapshot_dir / "profile.json").write_text(json.dumps(profile), encoding="utf-8")
    _break_database(monkeypatch)
    response = client.get("/")
    assert response.status_code == 503
    assert "Alex Jordan" in response.text
    assert "Saved summary." in response.text


def test_successful_request_saves_profile_for_later_outages(client, snapshot_dir):
    client.get("/")
    saved = json.loads((snapshot_dir / "profile.json").read_text(encoding="utf-8"))
    assert saved["name"] == "Alex Jordan"


def test_refresh_after_recovery_restores_projects_without_restart(client, snapshot_dir, monkeypatch):
    _break_database(monkeypatch)
    assert client.get("/").status_code == 503
    _restore_database(monkeypatch)
    response = client.get("/")
    assert response.status_code == 200
    assert "Featured project" in response.text
    assert "Projects temporarily unavailable" not in response.text


def test_project_page_returns_503_without_snapshot_when_database_fails(client, snapshot_dir, monkeypatch):
    (snapshot_dir / "projects").mkdir()
    (snapshot_dir / "projects" / "featured-project.html").write_text(SNAPSHOT_MARKER, encoding="utf-8")
    _break_database(monkeypatch)
    response = client.get("/projects/featured-project", headers={"accept": "text/html"})
    assert response.status_code == 503
    assert SNAPSHOT_MARKER not in response.text
