import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import get_settings
from app.db.models import Base, Profile, Project
from app.db import session as db_session_module
from app.main import create_app


@pytest.fixture
def client():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    db_session_module.engine = engine
    db_session_module.SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)
    Base.metadata.create_all(bind=engine)
    session = db_session_module.SessionLocal()
    session.add(
        Profile(
            name="Alex Jordan",
            headline="Business Transformation Leader",
            summary="Provides transformation leadership and operational improvement.",
            email="alex@example.com",
        )
    )
    session.add(
        Project(
            title="Featured project",
            slug="featured-project",
            summary="A featured transformation program.",
            publication_status="published",
            featured=True,
            display_order=1,
        )
    )
    session.commit()
    session.close()
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def e2e_client(tmp_path, monkeypatch):
    sqlite_path = tmp_path / "career_platform_e2e.db"
    snapshot_dir = tmp_path / "snapshots"
    dd = {
        "DATABASE_URL": f"sqlite:///{sqlite_path}",
        "SNAPSHOT_DIR": str(snapshot_dir),
        "SECRET_KEY": "test-secret",
        "ADMIN_PASSWORD": "pbkdf2_sha256$200000$Fvzz02RnT3msIEguSTqeKg==$2BYWgTJVHt0dFTiNHQ54vReZRxM4iAi4Ho6i791gvs4=",
        "ENVIRONMENT": "development",
    }
    for key, value in dd.items():
        monkeypatch.setenv(key, value)
    get_settings.cache_clear()
    engine = create_engine(f"sqlite:///{sqlite_path}", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    db_session_module.engine = engine
    db_session_module.SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)
    Base.metadata.create_all(bind=engine)
    session = db_session_module.SessionLocal()
    session.add(Profile(name="Alex Jordan", headline="Business Transformation Leader", summary="Leads transformation programs.", email="alex@example.com"))
    session.add(Project(title="Featured project", slug="featured-project", summary="A featured transformation story.", publication_status="published", featured=True, display_order=1))
    session.commit()
    session.close()
    app = create_app()
    with TestClient(app) as client:
        yield client
    Base.metadata.drop_all(bind=engine)
