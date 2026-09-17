from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ProjectMetricSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    label: str
    value: str
    display_order: int = 0


class MediaLinkSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    label: str
    url: str
    kind: str | None = None
    display_order: int = 0


class PublicProjectSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    slug: str
    summary: str
    featured: bool = False


class PublicProject(PublicProjectSummary):
    context: str | None = None
    problem: str | None = None
    responsibilities: str | None = None
    approach: str | None = None
    outcomes: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    organization_name: str | None = None
    role_name: str | None = None
    metrics: list[ProjectMetricSchema] = Field(default_factory=list)
    media_links: list[MediaLinkSchema] = Field(default_factory=list)


class PublicProfile(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    headline: str
    summary: str
    email: str | None = None
    phone: str | None = None
    location: str | None = None
