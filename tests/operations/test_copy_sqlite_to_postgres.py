from __future__ import annotations

from datetime import datetime

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.db.migrate import upgrade_to_head
from app.db.models import Base, MediaLink, Organization, Profile, Project, ProjectMetric, Role, Skill
from scripts.copy_sqlite_to_postgres import CopyError, copy_database

CREATED = datetime(2026, 9, 29, 21, 53, 49, 508812)


def make_source(path) -> str:
    url = f"sqlite:///{path}"
    engine = create_engine(url)
    Base.metadata.create_all(engine)
    with Session(engine) as s:
        org = Organization(id=7, name="LMU ITS", created_at=CREATED)
        role = Role(id=3, name="ITS Student Manager", created_at=CREATED)
        skill = Skill(id=5, name="ServiceNow", created_at=CREATED)
        s.add_all([org, role, skill])
        s.add(Profile(id=1, name="Caelon King", headline="H", summary="S", email="c@example.com", created_at=CREATED, updated_at=CREATED))
        project = Project(id=4, title="Dispatch", slug="dispatch", summary="S", publication_status="published", featured=True,
                          organization_id=7, role_id=3, display_order=1, created_at=CREATED, updated_at=CREATED)
        project.skills.append(skill)
        s.add(project)
        s.add(ProjectMetric(id=9, project_id=4, label="Users supported", value="10,000"))
        s.add(MediaLink(id=2, project_id=4, label="Demo", url="https://example.com"))
        s.commit()
    engine.dispose()
    return url


def migrated_sqlite_target(path) -> str:
    url = f"sqlite:///{path}"
    upgrade_to_head(url)
    return url


def test_copies_every_table_with_values_intact(tmp_path):
    counts = copy_database(make_source(tmp_path / "src.db"), migrated_sqlite_target(tmp_path / "dst.db"))
    assert counts["projects"] == 1 and counts["project_skills"] == 1 and counts["media_links"] == 1
    engine = create_engine(f"sqlite:///{tmp_path / 'dst.db'}")
    with Session(engine) as s:
        project = s.get(Project, 4)
        assert project.featured is True
        assert project.created_at == CREATED
        assert project.organization.name == "LMU ITS"
        assert [skill.name for skill in project.skills] == ["ServiceNow"]


def test_refuses_target_that_already_has_rows(tmp_path):
    source = make_source(tmp_path / "src.db")
    target = migrated_sqlite_target(tmp_path / "dst.db")
    copy_database(source, target)
    with pytest.raises(CopyError, match="not empty"):
        copy_database(source, target)


def test_refuses_target_not_at_head(tmp_path):
    with pytest.raises(CopyError, match="alembic upgrade head"):
        copy_database(make_source(tmp_path / "src.db"), f"sqlite:///{tmp_path / 'blank.db'}")


def test_postgres_copy_resets_id_sequences(tmp_path, postgres_url):
    upgrade_to_head(postgres_url)
    counts = copy_database(make_source(tmp_path / "src.db"), postgres_url)
    assert counts["profiles"] == 1
    engine = create_engine(postgres_url)
    with Session(engine) as s:
        s.add(Project(title="New", slug="new", summary="S", publication_status="draft", display_order=2))
        s.add(Organization(name="Another org"))
        s.commit()
        assert s.scalar(select(func.max(Project.id))) == 5
        assert s.scalar(select(Organization.id).where(Organization.name == "Another org")) == 8
    engine.dispose()
