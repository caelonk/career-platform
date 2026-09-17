from __future__ import annotations

from sqlalchemy.orm import Session

from app.db.models import Profile, Project
from app.repositories.content import get_public_profile as repo_get_public_profile
from app.repositories.content import get_public_project as repo_get_public_project
from app.repositories.content import list_public_projects as repo_list_public_projects
from app.schemas.content import PublicProfile, PublicProject, PublicProjectSummary, ProjectMetricSchema, MediaLinkSchema


def _project_metrics(project: Project):
    return [ProjectMetricSchema.model_validate(metric) for metric in project.metrics]


def _project_media(project: Project):
    return [MediaLinkSchema.model_validate(link) for link in project.media_links]


def get_public_profile(session: Session) -> PublicProfile | None:
    profile: Profile | None = repo_get_public_profile(session)
    if profile is None:
        return None
    return PublicProfile.model_validate(profile)


def list_public_projects(session: Session, featured_only: bool = False) -> list[PublicProjectSummary]:
    projects = repo_list_public_projects(session, featured_only=featured_only)
    return [PublicProjectSummary.model_validate(project) for project in projects]


def get_public_project(session: Session, slug: str) -> PublicProject | None:
    project: Project | None = repo_get_public_project(session, slug)
    if project is None:
        return None
    return PublicProject.model_validate(
        {
            **project.__dict__,
            "organization_name": project.organization.name if project.organization else None,
            "role_name": project.role.name if project.role else None,
            "metrics": _project_metrics(project),
            "media_links": _project_media(project),
        }
    )
