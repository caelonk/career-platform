from __future__ import annotations

import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.exc import SQLAlchemyError

from app.config import get_settings
from app.db import session as db_session_module
from app.services import profile_fallback
from app.services.public_content import get_public_profile, get_public_project, list_public_projects

logger = logging.getLogger(__name__)

SessionLocal = None


def _session_factory():
    factory = globals().get("SessionLocal")
    if callable(factory):
        return factory
    return db_session_module.SessionLocal


router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parents[1] / "templates"))

_MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def _split_date(value: str) -> tuple[str, str | None]:
    """Split a stored "YYYY" or "YYYY-MM" date into (year, month name)."""
    year, _, month = value.partition("-")
    if month.isdigit() and 1 <= int(month) <= 12:
        return year, _MONTHS[int(month) - 1]
    return year, None


def format_period(start: str | None, end: str | None) -> str:
    """Render a project's date range, e.g. "Jul – Aug 2026" or "Dec 2025 – Feb 2026"."""
    if not start:
        return ""
    start_year, start_month = _split_date(start)
    if not end:
        return f"{start_month} {start_year}" if start_month else start_year
    end_year, end_month = _split_date(end)
    end_text = f"{end_month} {end_year}" if end_month else end_year
    if start_year == end_year:
        if start_month and end_month and start_month != end_month:
            return f"{start_month} – {end_text}"
        return end_text
    start_text = f"{start_month} {start_year}" if start_month else start_year
    return f"{start_text} – {end_text}"


templates.env.filters["period"] = lambda project: format_period(project.start_date, project.end_date)


def _snapshot_dir() -> Path:
    return Path(get_settings().snapshot_dir)


@router.get("/", include_in_schema=False)
async def home(request: Request):
    session = _session_factory()()
    try:
        profile = get_public_profile(session)
        profile_fallback.remember(profile, _snapshot_dir())
        projects = list_public_projects(session)
    except SQLAlchemyError:
        # The database is down. Keep the profile visible, say so about projects, and
        # return 503 rather than old content, so the failure isn't hidden.
        logger.exception("Database read failed for the home page")
        context = {
            "request": request,
            "profile": profile_fallback.last_known(_snapshot_dir()),
            "featured_project": None,
            "projects": [],
            "projects_unavailable": True,
        }
        return templates.TemplateResponse(request, "public/home.html", context, status_code=503)
    finally:
        session.close()
    featured = next((project for project in projects if project.featured), None)
    context = {
        "request": request,
        "profile": profile,
        "featured_project": featured,
        "projects": [project for project in projects if project is not featured],
    }
    return templates.TemplateResponse(request, "public/home.html", context)


def _project_unavailable(request: Request):
    return templates.TemplateResponse(
        request,
        "errors/500.html",
        {"request": request, "detail": "This project is temporarily unavailable."},
        status_code=503,
    )


@router.get("/projects/{slug}", include_in_schema=False)
async def project_detail(request: Request, slug: str):
    session = _session_factory()()
    try:
        project = get_public_project(session, slug)
        if project is None:
            raise HTTPException(status_code=404, detail="Project not found.")
        published = list_public_projects(session)
        slugs = [summary.slug for summary in published]
        next_project = None
        if project.slug in slugs and len(slugs) > 1:
            next_project = published[(slugs.index(project.slug) + 1) % len(slugs)]
        context = {
            "request": request,
            "profile": get_public_profile(session),
            "project": project,
            "next_project": next_project,
        }
        return templates.TemplateResponse(request, "public/project.html", context)
    except SQLAlchemyError:
        logger.exception("Database read failed for project %s", slug)
        return _project_unavailable(request)
    finally:
        session.close()


PRIVACY_UPDATED = "October 15, 2026"
GA_MEASUREMENT_ID = "G-6J1F90ST16"
PRIVACY_CONTACT = "caelon@caelonk.me"


@router.get("/privacy", include_in_schema=False)
async def privacy(request: Request):
    session = _session_factory()()
    try:
        profile = get_public_profile(session)
    except Exception:
        profile = None
    finally:
        session.close()
    context = {
        "request": request,
        "profile": profile,
        "updated": PRIVACY_UPDATED,
        "ga_measurement_id": GA_MEASUREMENT_ID,
        "privacy_contact": PRIVACY_CONTACT,
    }
    return templates.TemplateResponse(request, "public/privacy.html", context)


@router.get("/resume.pdf", include_in_schema=False)
async def resume_pdf():
    resume_file = Path(__file__).resolve().parents[1] / "static" / "resume" / "resume.pdf"
    if not resume_file.exists():
        raise HTTPException(status_code=404, detail="Resume not available.")
    return FileResponse(resume_file)
