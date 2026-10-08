from __future__ import annotations

from app.config import get_settings
from app.db.models import Base, Profile, Project
from app.db.session import SessionLocal, engine


def setup_seed_data():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    try:
        profile = Profile(
            name="Alex Jordan",
            headline="Business Transformation Leader",
            summary="Leads strategic transformation programs and measurable operating-model change.",
            email="alex@example.com",
        )
        session.add(profile)
        project = Project(
            title="Featured project",
            slug="featured-project",
            summary="Delivered a major operating-model redesign.",
            publication_status="published",
            featured=True,
            display_order=1,
        )
        draft = Project(
            title="Draft Project",
            slug="draft-project",
            summary="Hidden while in development.",
            publication_status="draft",
            featured=False,
            display_order=2,
        )
        session.add_all([project, draft])
        session.commit()
    finally:
        session.close()


def test_home_page_contains_profile_and_featured_project(client):
    setup_seed_data()
    response = client.get("/")
    assert response.status_code == 200
    assert "Business Transformation" in response.text
    assert "Featured project" in response.text


def test_draft_project_is_not_public(client):
    setup_seed_data()
    response = client.get("/projects/draft-project")
    assert response.status_code == 404


def test_home_lists_featured_project_once_without_roadmap(client):
    setup_seed_data()
    response = client.get("/")
    assert response.text.count('href="/projects/featured-project"') == 1
    assert "Roadmap" not in response.text
    assert 'href="/auth/login"' not in response.text


def test_unknown_project_renders_html_404_for_browsers(client):
    setup_seed_data()
    response = client.get("/projects/no-such-project", headers={"accept": "text/html"})
    assert response.status_code == 404
    assert response.headers["content-type"].startswith("text/html")
    assert "See all projects" in response.text


def test_unknown_project_keeps_json_404_for_api_clients(client):
    setup_seed_data()
    response = client.get("/projects/no-such-project", headers={"accept": "application/json"})
    assert response.status_code == 404
    assert response.json() == {"detail": "Project not found."}


def test_format_period():
    from app.routes.public import format_period

    assert format_period(None, None) == ""
    assert format_period("2025", None) == "2025"
    assert format_period("2026-01", None) == "Jan 2026"
    assert format_period("2026-07", "2026-08") == "Jul – Aug 2026"
    assert format_period("2026-07", "2026-07") == "Jul 2026"
    assert format_period("2025-12", "2026-02") == "Dec 2025 – Feb 2026"
    assert format_period("2024", "2025") == "2024 – 2025"
