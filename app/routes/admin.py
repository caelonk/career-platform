from __future__ import annotations

from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.config import get_settings
from app.db import session as db_session_module
from app.db.models import Project
from app.repositories.content import create_project
from app.services.auth import require_admin
from app.services.snapshots import generate_public_snapshot

SessionLocal = None


def _session_factory():
    factory = globals().get("SessionLocal")
    if callable(factory):
        return factory
    return db_session_module.SessionLocal


router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parents[1] / "templates"))


def _make_unique_slug(session, slug: str) -> str:
    candidate = slug
    suffix = 1
    while session.execute(select(Project).where(Project.slug == candidate)).scalar_one_or_none() is not None:
        candidate = f"{slug}-{suffix}"
        suffix += 1
    return candidate


@router.get("/admin")
async def admin_dashboard(request: Request):
    require_admin(request)
    session = _session_factory()()
    try:
        projects = session.query(Project).order_by(Project.display_order.asc(), Project.id.asc()).all()
        return templates.TemplateResponse(request, "admin/dashboard.html", {"request": request, "projects": projects})
    finally:
        session.close()


@router.get("/admin/projects/new")
async def admin_new_project(request: Request):
    require_admin(request)
    return templates.TemplateResponse(request, "admin/project_form.html", {"request": request, "project": None, "error": None})


@router.post("/admin/projects")
async def create_admin_project(
    request: Request,
    title: str = Form(...),
    slug: str = Form(...),
    summary: str = Form(...),
    publication_status: str = Form("draft"),
):
    require_admin(request)
    session = _session_factory()()
    try:
        existing = session.execute(select(Project).where(Project.slug == slug)).scalar_one_or_none()
        if existing is not None:
            existing.title = title
            existing.summary = summary
            existing.publication_status = publication_status
            existing.featured = publication_status == "published"
            if publication_status == "published":
                existing.published_at = existing.published_at or datetime.utcnow()
            project = existing
        else:
            unique_slug = _make_unique_slug(session, slug)
            project = create_project(
                session,
                title=title,
                slug=unique_slug,
                summary=summary,
                publication_status=publication_status,
                featured=publication_status == "published",
            )
        if publication_status == "published":
            generate_public_snapshot(session, Path(get_settings().snapshot_dir))
        session.commit()
        return RedirectResponse(url="/admin", status_code=303)
    except (IntegrityError, SQLAlchemyError, ValueError):
        session.rollback()
        raise HTTPException(status_code=400, detail="Unable to save project.")
    finally:
        session.close()


@router.get("/admin/projects/{project_id}/edit")
async def admin_edit_project(request: Request, project_id: int):
    require_admin(request)
    session = _session_factory()()
    try:
        project = session.get(Project, project_id)
        if project is None:
            raise HTTPException(status_code=404, detail="Project not found.")
        return templates.TemplateResponse(request, "admin/project_form.html", {"request": request, "project": project, "error": None})
    finally:
        session.close()


@router.post("/admin/projects/{project_id}")
async def update_admin_project(
    request: Request,
    project_id: int,
    title: str = Form(...),
    slug: str = Form(...),
    summary: str = Form(...),
    publication_status: str = Form("draft"),
):
    require_admin(request)
    session = _session_factory()()
    try:
        project = session.get(Project, project_id)
        if project is None:
            raise HTTPException(status_code=404, detail="Project not found.")
        project.title = title
        existing_same_slug = session.execute(select(Project).where(Project.slug == slug, Project.id != project_id)).scalar_one_or_none()
        project.slug = slug if existing_same_slug is None else _make_unique_slug(session, slug)
        project.summary = summary
        project.publication_status = publication_status
        project.featured = publication_status == "published"
        if publication_status == "published":
            project.published_at = project.published_at or datetime.utcnow()
        session.commit()
        generate_public_snapshot(session, Path(get_settings().snapshot_dir))
        return RedirectResponse(url="/admin", status_code=303)
    except (IntegrityError, SQLAlchemyError):
        session.rollback()
        raise HTTPException(status_code=400, detail="Unable to update project.")
    finally:
        session.close()
