from __future__ import annotations

from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import session as db_session_module
from app.db.migrate import upgrade_to_head
from app.db.models import Base, Profile, Project
from app.main import create_app


def test_migrations_match_models_on_postgres(postgres_url):
    upgrade_to_head(postgres_url)
    engine = create_engine(postgres_url)
    with engine.connect() as connection:
        diff = compare_metadata(MigrationContext.configure(connection), Base.metadata)
    engine.dispose()
    assert diff == []


def test_public_pages_render_from_postgres(postgres_url):
    upgrade_to_head(postgres_url)
    engine = create_engine(postgres_url)
    db_session_module.engine = engine
    db_session_module.SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)
    with db_session_module.SessionLocal() as session:
        session.add(Profile(name="Alex Jordan", headline="Builder · Systems", summary="Builds things.", email="alex@example.com"))
        session.add(Project(title="Featured project", slug="featured-project", summary="A story.", publication_status="published", featured=True, display_order=1))
        session.add(Project(title="Draft", slug="draft", summary="Hidden.", publication_status="draft", display_order=2))
        session.commit()
    with TestClient(create_app()) as client:
        assert client.get("/").status_code == 200
        assert "Featured project" in client.get("/projects/featured-project").text
        assert client.get("/projects/draft").status_code == 404
    engine.dispose()
