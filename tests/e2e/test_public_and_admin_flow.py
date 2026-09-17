from __future__ import annotations


def test_recruiter_flow_and_admin_publication(e2e_client):
    home = e2e_client.get("/")
    assert home.status_code == 200
    assert "Business Transformation" in home.text
    login = e2e_client.post("/auth/login", data={"username": "admin", "password": "admin-password"}, follow_redirects=False)
    assert login.status_code in {200, 303}
    draft = e2e_client.post(
        "/admin/projects",
        data={"title": "New Case Study", "slug": "new-case-study", "summary": "A newly prepared case study.", "publication_status": "draft"},
        follow_redirects=False,
    )
    assert draft.status_code == 303
    assert e2e_client.get("/projects/new-case-study").status_code == 404
    publish = e2e_client.post(
        "/admin/projects",
        data={"title": "New Case Study", "slug": "new-case-study", "summary": "A newly prepared case study.", "publication_status": "published"},
        follow_redirects=False,
    )
    assert publish.status_code == 303
    assert e2e_client.get("/projects/new-case-study").status_code == 200
