from __future__ import annotations

from datetime import datetime

import pytest
from sqlalchemy import select

from app.db.models import Base, Experience, MediaLink, Organization, Project, ProjectMetric, Role, Skill
from app.db.session import SessionLocal, engine


@pytest.fixture
def db_session():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


def test_project_can_link_metrics_skills_and_media(db_session):
    organization = Organization(name="Contoso")
    role = Role(name="Transformation Lead")
    skill = Skill(name="Transformation", category="Strategy")
    project = Project(
        title="Business Transformation Program",
        slug="business-transformation-program",
        summary="Modernized operating model and delivery outcomes.",
        publication_status="published",
        featured=True,
        start_date="2024-01",
        end_date="2024-12",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        organization=organization,
        role=role,
    )
    project.metrics.append(ProjectMetric(label="Savings", value="30%", display_order=1))
    project.skills.append(skill)
    project.media_links.append(MediaLink(label="Diagram", url="https://example.com/diagram.jpg", kind="image", display_order=1))

    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)

    assert project.metrics[0].value == "30%"
    assert project.skills[0].name == "Transformation"
    assert project.media_links[0].url.startswith("https://")

    saved = db_session.execute(select(Project).where(Project.slug == "business-transformation-program")).scalar_one()
    assert saved.publication_status == "published"


def test_experience_can_have_skills(db_session):
    skill = Skill(name="Stakeholder Management", category="Leadership")
    organization = Organization(name="Northwind")
    experience = Experience(
        title="Transformation Manager",
        summary="Led enterprise transformation workstreams.",
        organization=organization,
        start_date="2023-01",
        end_date="2024-01",
        display_order=1,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    experience.skills.append(skill)

    db_session.add(experience)
    db_session.commit()
    db_session.refresh(experience)

    assert experience.skills[0].name == "Stakeholder Management"
