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
