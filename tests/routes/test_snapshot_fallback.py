from __future__ import annotations

from pathlib import Path

from app.db.models import Base, Profile, Project
from app.db.session import SessionLocal, engine


def seed_live_content():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    try:
        session.add(Profile(name="Alex Jordan", headline="Business Transformation Leader", summary="Strategy and transformation leadership.", email="alex@example.com"))
        session.add(Project(title="Transformation Program", slug="transformation-program", summary="Program summary", publication_status="published", featured=True))
        session.commit()
    finally:
        session.close()


def test_home_page_keeps_profile_visible_when_database_is_unavailable(client, monkeypatch, tmp_path):
    seed_live_content()
    snapshot_dir = tmp_path / "snapshots"
    snapshot_dir.mkdir()
    (snapshot_dir / "home.html").write_text("<html><body>Business Transformation Contact</body></html>", encoding="utf-8")
    monkeypatch.setattr("app.routes.public.SessionLocal", lambda: _BrokenSession())
    monkeypatch.setattr("app.routes.public.get_settings", lambda: type("Settings", (), {"snapshot_dir": str(snapshot_dir)})())
    response = client.get("/")
    assert response.status_code == 200
    assert "Business Transformation" in response.text
    assert "Contact" in response.text


class _BrokenSession:
    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def close(self):
        pass
