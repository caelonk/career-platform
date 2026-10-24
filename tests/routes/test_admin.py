from __future__ import annotations

import pytest

from app.config import get_settings


@pytest.fixture
def admin_client(client):
    return client


def test_admin_redirects_anonymous_user(client):
    response = client.get("/admin", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/auth/login"


def test_admin_can_create_draft_project(client):
    response = client.post(
        "/auth/login",
        data={"username": "admin", "password": "admin-password"},
        follow_redirects=False,
    )
    assert response.status_code in {200, 303}
    create_response = client.post(
        "/admin/projects",
        data={"title": "Transformation", "slug": "transformation", "summary": "A major transformation effort.", "publication_status": "draft"},
        follow_redirects=False,
    )
    assert create_response.status_code == 303


def test_admin_dashboard_does_not_load_analytics(client):
    client.post("/auth/login", data={"username": "admin", "password": "admin-password"}, follow_redirects=False)
    response = client.get("/admin")
    assert response.status_code == 200
    assert "googletagmanager.com" not in response.text


SLUG_ERROR = "Slug can&#39;t be blank or contain spaces"


def _log_in(client):
    client.post("/auth/login", data={"username": "admin", "password": "admin-password"}, follow_redirects=False)


def _slugs():
    from app.db import session as db_session_module
    from app.db.models import Project

    session = db_session_module.SessionLocal()
    try:
        return sorted(project.slug for project in session.query(Project).all())
    finally:
        session.close()


@pytest.mark.parametrize("bad_slug", ["", " ", "   ", "in progress", "tab\tslug", " leading", "trailing "])
def test_create_rejects_blank_or_spaced_slug(client, bad_slug):
    _log_in(client)
    before = _slugs()
    response = client.post(
        "/admin/projects",
        data={"title": "This website", "slug": bad_slug, "summary": "In progress.", "publication_status": "draft"},
        follow_redirects=False,
    )
    assert response.status_code == 400
    assert SLUG_ERROR in response.text
    assert 'value="This website"' in response.text
    assert _slugs() == before


@pytest.mark.parametrize("bad_slug", [" ", "in progress"])
def test_edit_rejects_blank_or_spaced_slug(client, bad_slug):
    _log_in(client)
    response = client.post(
        "/admin/projects/1",
        data={"title": "Featured project", "slug": bad_slug, "summary": "Changed.", "publication_status": "published"},
        follow_redirects=False,
    )
    assert response.status_code == 400
    assert SLUG_ERROR in response.text
    assert _slugs() == ["featured-project"]


def test_edit_keeps_working_with_a_valid_slug(client):
    _log_in(client)
    response = client.post(
        "/admin/projects/1",
        data={"title": "Featured project", "slug": "caelonk-me", "summary": "Changed.", "publication_status": "published"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert _slugs() == ["caelonk-me"]


def test_project_form_hints_that_slugs_have_no_spaces(client):
    _log_in(client)
    response = client.get("/admin/projects/new")
    assert 'pattern="[^\s]+"' in response.text


def _featured_by_slug():
    from app.db import session as db_session_module
    from app.db.models import Project

    session = db_session_module.SessionLocal()
    try:
        return {project.slug: project.featured for project in session.query(Project).all()}
    finally:
        session.close()


def test_publishing_a_new_project_does_not_feature_it_unless_ticked(client):
    _log_in(client)
    client.post(
        "/admin/projects",
        data={"title": "Second", "slug": "second", "summary": "Not featured.", "publication_status": "published"},
        follow_redirects=False,
    )
    assert _featured_by_slug()["second"] is False


def test_new_project_is_featured_when_ticked(client):
    _log_in(client)
    client.post(
        "/admin/projects",
        data={"title": "Second", "slug": "second", "summary": "Featured.", "publication_status": "published", "featured": "true"},
        follow_redirects=False,
    )
    assert _featured_by_slug()["second"] is True


def test_unticking_featured_on_edit_unfeatures_a_published_project(client):
    _log_in(client)
    assert _featured_by_slug()["featured-project"] is True
    response = client.post(
        "/admin/projects/1",
        data={"title": "Featured project", "slug": "featured-project", "summary": "Still published.", "publication_status": "published"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert _featured_by_slug()["featured-project"] is False


def test_ticking_featured_on_edit_keeps_it_featured(client):
    _log_in(client)
    client.post(
        "/admin/projects/1",
        data={"title": "Featured project", "slug": "featured-project", "summary": "Still published.", "publication_status": "published", "featured": "true"},
        follow_redirects=False,
    )
    assert _featured_by_slug()["featured-project"] is True


def test_edit_form_shows_featured_checkbox_state(client):
    _log_in(client)
    response = client.get("/admin/projects/1/edit")
    assert 'name="featured" value="true" checked' in response.text
