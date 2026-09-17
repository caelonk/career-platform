from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.models import Base, MediaLink, Profile, Project, ProjectMetric
from app.repositories.content import create_project, get_public_project, list_public_projects
from app.services.public_content import get_public_profile, list_public_projects as list_public_projects_service


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    SessionLocal = sessionmaker(bind=engine)
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def test_public_project_query_excludes_drafts_and_archived(db_session):
    create_project(db_session, title="Published Project", slug="published-project", summary="Visible project", publication_status="published")
    create_project(db_session, title="Draft Project", slug="draft-project", summary="Hidden", publication_status="draft")
    create_project(db_session, title="Archived Project", slug="archived-project", summary="Hidden too", publication_status="archived")

    projects = list_public_projects(db_session)

    assert [project.slug for project in projects] == ["published-project"]
    assert get_public_project(db_session, "draft-project") is None


def test_featured_projects_only_return_featured_items(db_session):
    create_project(db_session, title="Featured Project", slug="featured-project", summary="Featured", publication_status="published", featured=True, display_order=1)
    create_project(db_session, title="Standard Project", slug="standard-project", summary="Not featured", publication_status="published", featured=False, display_order=2)

    projects = list_public_projects(db_session, featured_only=True)

    assert [project.slug for project in projects] == ["featured-project"]


def test_profile_service_returns_public_fields_only(db_session):
    profile = Profile(name="Alex Jordan", headline="Business Transformation Leader", summary="Helps teams deliver change.", email="alex@example.com", phone="555-1111", location="Seattle")
    db_session.add(profile)
    db_session.commit()

    public_profile = get_public_profile(db_session)

    assert public_profile is not None
    assert public_profile.name == "Alex Jordan"
    assert public_profile.email == "alex@example.com"
    assert public_profile.phone == "555-1111"


def test_public_project_service_maps_related_fields(db_session):
    project = create_project(
        db_session,
        title="Delivery Transformation",
        slug="delivery-transformation",
        summary="Implementation program",
        publication_status="published",
        featured=True,
        context="Client context",
        problem="Legacy process",
        responsibilities="Led the workstream",
        approach="Lean operating model",
        outcomes="Reduced cycle time",
    )
    project.metrics.append(ProjectMetric(label="Savings", value="30%", display_order=1))
    project.media_links.append(MediaLink(label="Diagram", url="https://example.com/diagram.jpg", kind="image", display_order=1))
    db_session.commit()

    public_project = list_public_projects_service(db_session)[0]

    assert public_project.title == "Delivery Transformation"
    assert public_project.slug == "delivery-transformation"
