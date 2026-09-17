from __future__ import annotations

from pathlib import Path

import pytest

from app.config import get_settings
from app.db.models import Base, Profile, Project
from app.db.session import SessionLocal, engine
from app.services.snapshots import SnapshotGenerationError, generate_public_snapshot


@pytest.fixture
def seeded_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    try:
        profile = Profile(
            name="Alex Jordan",
            headline="Business Transformation Leader",
            summary="Helps teams deliver change.",
            email="alex@example.com",
        )
        session.add(profile)
        session.add(
            Project(
                title="Strategy Program",
                slug="strategy-program",
                summary="Strategy execution program.",
                publication_status="published",
                featured=True,
            )
        )
        session.commit()
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


def test_failed_generation_does_not_replace_previous_snapshot(tmp_path, seeded_db):
    snapshot_dir = tmp_path / "snapshots"
    snapshot_dir.mkdir()
    initial = snapshot_dir / "manifest.json"
    initial.write_text('{"version": "1"}', encoding="utf-8")

    with pytest.raises(SnapshotGenerationError):
        generate_public_snapshot(seeded_db, snapshot_dir)

    assert initial.exists()


def test_snapshot_generation_writes_manifest(tmp_path, seeded_db):
    snapshot_dir = tmp_path / "snapshots"
    manifest = generate_public_snapshot(seeded_db, snapshot_dir)
    assert manifest.profile_path == "home.html"
    assert (snapshot_dir / "home.html").exists()
    assert (snapshot_dir / "manifest.json").exists()
