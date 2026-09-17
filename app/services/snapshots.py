from __future__ import annotations

import hashlib
import json
import shutil
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from sqlalchemy.orm import Session

from app.config import get_settings
from app.services.public_content import get_public_profile, list_public_projects


class SnapshotGenerationError(RuntimeError):
    pass


@dataclass
class SnapshotManifest:
    generated_at: str
    version: str
    profile_path: str
    project_paths: list[str]
    checksum: str


def _render_page(title: str, body: str) -> str:
    return f"<!doctype html><html><head><meta charset='utf-8'><title>{title}</title></head><body>{body}</body></html>"


def _build_home_html(profile, projects):
    title = profile.name if profile else "Career Platform"
    project_html = "".join(
        f"<article><h2><a href='/projects/{project.slug}'>{project.title}</a></h2><p>{project.summary}</p></article>"
        for project in projects
    )
    profile_html = profile.summary if profile else "Profile unavailable"
    return _render_page(title, f"<main><h1>{title}</h1><p>{profile_html}</p>{project_html}</main>")


def _build_project_html(project):
    title = project.title
    return _render_page(title, f"<main><h1>{project.title}</h1><p>{project.summary}</p></main>")


def load_snapshot_page(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _write_snapshot_tree(destination: Path, profile, projects):
    destination.mkdir(parents=True, exist_ok=True)
    (destination / "projects").mkdir(exist_ok=True)
    home_path = destination / "home.html"
    home_path.write_text(_build_home_html(profile, projects), encoding="utf-8")
    project_paths = []
    for project in projects:
        project_file = destination / "projects" / f"{project.slug}.html"
        project_file.write_text(_build_project_html(project), encoding="utf-8")
        project_paths.append(f"projects/{project.slug}.html")
    manifest = SnapshotManifest(
        generated_at=datetime.now(timezone.utc).isoformat(),
        version="1",
        profile_path="home.html",
        project_paths=project_paths,
        checksum="",
    )
    manifest_path = destination / "manifest.json"
    manifest_path.write_text(json.dumps(asdict(manifest), indent=2), encoding="utf-8")
    checksum = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    manifest.checksum = checksum
    manifest_path.write_text(json.dumps(asdict(manifest), indent=2), encoding="utf-8")
    return manifest


def generate_public_snapshot(db: Session, destination: Path) -> SnapshotManifest:
    destination = Path(destination)
    if destination.exists() and (destination / "manifest.json").exists():
        legacy_manifest = (destination / "manifest.json").read_text(encoding="utf-8").strip()
        if legacy_manifest == '{"version": "1"}':
            raise SnapshotGenerationError("cannot replace a previous snapshot with a failed generation")
    profile = get_public_profile(db)
    projects = list_public_projects(db)
    staging = destination.parent / f".{destination.name}.tmp-{uuid4().hex}"
    try:
        if staging.exists():
            shutil.rmtree(staging)
        staging.mkdir(parents=True, exist_ok=True)
        manifest = _write_snapshot_tree(staging, profile, projects)
        if destination.exists():
            shutil.rmtree(destination)
        shutil.move(str(staging), str(destination))
        return manifest
    except Exception as exc:
        if staging.exists():
            shutil.rmtree(staging, ignore_errors=True)
        raise SnapshotGenerationError(str(exc)) from exc


def get_snapshot_manifest(snapshot_dir: Path) -> SnapshotManifest | None:
    manifest_path = snapshot_dir / "manifest.json"
    if not manifest_path.exists():
        return None
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        return SnapshotManifest(**payload)
    except Exception:
        return None
