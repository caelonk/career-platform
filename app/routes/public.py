from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.exc import SQLAlchemyError

from app.config import get_settings
from app.db import session as db_session_module
from app.services.public_content import get_public_profile, get_public_project, list_public_projects
from app.services.snapshots import load_snapshot_page

SessionLocal = None


def _session_factory():
    factory = globals().get("SessionLocal")
    if callable(factory):
        return factory
    return db_session_module.SessionLocal


router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parents[1] / "templates"))

PLACEHOLDER_SECTIONS = [
    {"title": "Case studies in progress", "description": "A deeper transformation narrative and client story is being prepared."},
    {"title": "Career tools coming soon", "description": "A curated set of frameworks and templates will be shared here."},
    {"title": "Insights coming soon", "description": "A regular stream of strategy reflections and lessons will appear soon."},
]


def _snapshot_path_for(page_name: str) -> Path:
    snapshot_dir = Path(get_settings().snapshot_dir)
    return snapshot_dir / f"{page_name}.html"


def _fallback_snapshot(page_name: str) -> HTMLResponse | None:
    snapshot_file = _snapshot_path_for(page_name)
    if snapshot_file.exists():
        return HTMLResponse(load_snapshot_page(snapshot_file))
    return None


@router.get("/", include_in_schema=False)
async def home(request: Request):
    session = _session_factory()()
    try:
        profile = get_public_profile(session)
        featured = list_public_projects(session, featured_only=True)
        projects = list_public_projects(session)
        context = {
            "request": request,
            "profile": profile,
            "featured_projects": featured,
            "projects": projects,
            "placeholder_sections": PLACEHOLDER_SECTIONS,
        }
        return templates.TemplateResponse(request, "public/home.html", context)
    except Exception:
        fallback = _fallback_snapshot("home")
        if fallback is not None:
            return fallback
        raise HTTPException(status_code=404, detail="Resume profile unavailable.")
    finally:
        session.close()


@router.get("/projects/{slug}", include_in_schema=False)
async def project_detail(request: Request, slug: str):
    session = _session_factory()()
    try:
        project = get_public_project(session, slug)
        if project is None:
            fallback = _fallback_snapshot(f"projects/{slug}")
            if fallback is not None:
                return fallback
            raise HTTPException(status_code=404, detail="Project not found.")
        return templates.TemplateResponse(request, "public/project.html", {"request": request, "project": project})
    except Exception:
        fallback = _fallback_snapshot(f"projects/{slug}")
        if fallback is not None:
            return fallback
        raise HTTPException(status_code=404, detail="Project not found.")
    finally:
        session.close()


@router.get("/resume.pdf", include_in_schema=False)
async def resume_pdf():
    resume_file = Path(__file__).resolve().parents[1] / "static" / "resume" / "resume.pdf"
    if not resume_file.exists():
        raise HTTPException(status_code=404, detail="Resume not available.")
    return FileResponse(resume_file)
