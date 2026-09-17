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
