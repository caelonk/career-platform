from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Profile, Project


def create_project(
    session: Session,
    *,
    title: str,
    slug: str,
    summary: str,
    publication_status: str = "draft",
    featured: bool = False,
    context: str | None = None,
    problem: str | None = None,
    responsibilities: str | None = None,
    approach: str | None = None,
    outcomes: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    display_order: int = 0,
) -> Project:
    project = Project(
        title=title,
        slug=slug,
        summary=summary,
        publication_status=publication_status,
        featured=featured,
        context=context,
        problem=problem,
        responsibilities=responsibilities,
        approach=approach,
        outcomes=outcomes,
        start_date=start_date,
        end_date=end_date,
        display_order=display_order,
    )
    session.add(project)
    session.commit()
    session.refresh(project)
    return project


def get_public_profile(session: Session) -> Profile | None:
    return session.execute(select(Profile).order_by(Profile.id)).scalars().first()


def list_public_projects(session: Session, featured_only: bool = False):
    query = select(Project).where(Project.publication_status == "published")
    if featured_only:
        query = query.where(Project.featured.is_(True))
    query = query.order_by(Project.display_order.asc(), Project.published_at.desc().nulls_last(), Project.id.asc())
    return session.execute(query).scalars().all()


def get_public_project(session: Session, slug: str) -> Project | None:
    return session.execute(
        select(Project).where(Project.slug == slug, Project.publication_status == "published")
    ).scalar_one_or_none()
