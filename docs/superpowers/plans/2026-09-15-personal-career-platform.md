# Personal Career Platform Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a recruiter-friendly personal resume and case-study site with FastAPI, Jinja templates, a typed SQLAlchemy data layer, authenticated administration, and a database-independent public snapshot fallback.

**Architecture:** The application is a server-rendered FastAPI service behind Nginx on an Azure Linux VM. Jinja templates render public and admin pages; application services enforce publication and visibility rules; SQLAlchemy 2.x repositories access SQLite locally/tests and Azure Database for PostgreSQL in production; Alembic owns schema migrations. systemd manages Uvicorn, while Nginx handles TLS, static assets, snapshot fallback, and reverse proxying. Public pages use live database reads when available and fall back to versioned static HTML/JSON files when the database is unavailable.

**Tech Stack:** Python 3.12, FastAPI, Uvicorn, Jinja2, SQLAlchemy 2.x, Alembic, Pydantic v2, SQLite for local development/tests, Azure Database for PostgreSQL, pytest, httpx, Nginx, systemd, Azure Linux VM, vanilla CSS, and server-side signed session cookies with password hashing.

**Spec:** `docs/superpowers/specs/2026-09-15-personal-career-platform-design.md`

## Global Constraints

- The public experience is a hybrid executive profile, resume, and featured transformation case-study site.
- Major future modules may use specific public placeholders; incomplete resume content remains hidden.
- PostgreSQL is the production system of record; SQLite is used only for local development and tests.
- The browser never connects directly to PostgreSQL or receives database credentials.
- The application uses server-side loaders/actions equivalent to FastAPI route handlers and services.
- The profile identity, headline, value proposition, contact or resume CTA, and core resume content must remain visible from the last good snapshot during a database outage.
- Snapshot generation must never replace a valid snapshot with a failed or partial generation.
- The initial release uses validated external media URLs and serves the resume PDF as a static application asset; it does not implement uploads.
- Production recovery targets are RPO 24 hours and RTO 4 hours.
- Production runs on an Azure Linux VM with Nginx and systemd-managed Uvicorn; PostgreSQL runs on Azure Database for PostgreSQL.
- Public queries include only published and visible records; private or draft records never enter public payloads.
- Failed writes and database errors must return explicit failure responses, never success-shaped fallbacks.

---

## File and module map

Create the following focused boundaries:

- `pyproject.toml`: runtime, development, and test dependencies plus command configuration.
- `.env.example`: documented local and production configuration keys without secrets.
- `Dockerfile`, `docker-compose.yml`: optional reproducible local application and database development services.
- `deploy/nginx/career-platform.conf`: Nginx TLS, static-file, snapshot-fallback, and reverse-proxy configuration.
- `deploy/systemd/career-platform.service`: systemd service for Uvicorn on the Azure VM.
- `deploy/azure/README.md`: Azure VM, managed PostgreSQL, firewall, DNS, TLS, deployment, and rollback runbook.
- `app/main.py`: FastAPI application factory, middleware, router registration, and startup checks.
- `app/config.py`: typed environment configuration.
- `app/db/session.py`: SQLAlchemy engine/session construction and request-scoped session dependency.
- `app/db/models.py`: SQLAlchemy models and relationship tables.
- `app/db/migrations/`: Alembic environment and version scripts.
- `app/schemas/content.py`, `app/schemas/auth.py`: request/response validation models.
- `app/repositories/content.py`, `app/repositories/admin.py`: typed database access functions.
- `app/services/public_content.py`: publication-filtered reads and public view models.
- `app/services/snapshots.py`: atomic snapshot generation, validation, and fallback reads.
- `app/services/auth.py`: password hashing and session authentication.
- `app/routes/public.py`: public profile, resume, and project routes.
- `app/routes/admin.py`, `app/routes/auth.py`: authenticated administration and login/logout routes.
- `app/templates/`: public, admin, auth, and error templates.
- `app/static/css/site.css`: accessible recruiter-focused visual system.
- `app/static/resume/resume.pdf`: versioned resume asset location.
- `tests/`: unit, integration, and end-to-end route tests.
- `tests/operations/test_deployment_config.py`: static checks for Nginx and systemd deployment contracts.
- `scripts/restore_verify.py`: isolated restore and recovery verification entry point.
- `docs/operations/recovery.md`: backup, restore, RPO/RTO, and verification instructions.

## Tasks

### Task 1: Creating the runnable FastAPI foundation

**Files:**
- Create: `pyproject.toml`
- Create: `.env.example`
- Create: `app/__init__.py`
- Create: `app/main.py`
- Create: `app/config.py`
- Create: `app/templates/errors/500.html`
- Create: `app/static/css/site.css`
- Create: `Dockerfile`
- Create: `docker-compose.yml`
- Create: `deploy/nginx/career-platform.conf`
- Create: `deploy/systemd/career-platform.service`
- Create: `deploy/azure/README.md`
- Test: `tests/test_health.py`

**Interfaces:**
- Produces `create_app() -> FastAPI`.
- Produces `Settings` with `database_url`, `secret_key`, `snapshot_dir`, and `environment`.
- Produces `GET /health` returning `{"status": "ok"}` when the process is healthy.

- [ ] **Step 1: Write the failing health test**

```python
def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

- [ ] **Step 2: Run the test and verify it fails**

Run: `pytest tests/test_health.py -q`
Expected: FAIL because the application package and health route do not exist.

- [ ] **Step 3: Add the application configuration and factory**

Define environment-backed settings with a safe test default for SQLite, reject an empty production secret key, and register the health route from `create_app()`.

- [ ] **Step 4: Add the development container files and base templates**

Configure Docker Compose for optional local development with a mounted source tree and snapshot directory. Keep PostgreSQL available as an optional local service while the default test database remains SQLite. The production process will not depend on Docker Compose.

- [ ] **Step 5: Run the test and verify it passes**

Run: `pytest tests/test_health.py -q`
Expected: PASS.

**Done looks like:** A fresh checkout can install dependencies, construct the FastAPI app, serve `/health`, and load the base CSS/template without importing database-specific application code.

**How to check:** Run `python -m pytest tests/test_health.py -q` and `docker compose config`; both complete successfully.

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml .env.example app Dockerfile docker-compose.yml tests/test_health.py
git commit -m "feat: create FastAPI application foundation"
```

### Task 2: Building the SQLAlchemy schema and migrations

**Files:**
- Create: `app/db/session.py`
- Create: `app/db/models.py`
- Create: `app/db/migrations/env.py`
- Create: `app/db/migrations/script.py.mako`
- Create: `app/db/migrations/versions/0001_initial_content_schema.py`
- Create: `tests/db/test_schema.py`
- Modify: `app/main.py`

**Interfaces:**
- Produces `get_db() -> Generator[Session, None, None]`.
- Produces models for `Profile`, `Organization`, `Role`, `Experience`, `Skill`, `Certification`, `Achievement`, `Project`, `ProjectMetric`, `MediaLink`, and explicit many-to-many association tables.
- Produces `Project.publication_status` values `draft`, `published`, and `archived`.
- Produces `Project.slug` uniqueness and publication/date constraints.

- [ ] **Step 1: Write schema tests for relationships and constraints**

```python
def test_project_can_link_metrics_skills_and_media(db_session):
    project = published_project()
    project.metrics.append(ProjectMetric(label="Savings", value="30%"))
    project.skills.append(Skill(name="Transformation"))
    project.media_links.append(MediaLink(url="https://example.com/image.jpg", label="Diagram"))
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)
    assert project.metrics[0].value == "30%"
    assert project.skills[0].name == "Transformation"
    assert project.media_links[0].url.startswith("https://")
```

- [ ] **Step 2: Run the schema tests and verify they fail**

Run: `pytest tests/db/test_schema.py -q`
Expected: FAIL because the SQLAlchemy models and session fixture do not exist.

- [ ] **Step 3: Implement the models and session factory**

Use SQLAlchemy 2.x typed declarative mappings, UUID or integer primary keys consistently, timezone-aware timestamps, explicit ordering fields, and foreign-key relationships. Keep media as validated URL metadata rather than upload blobs.

- [ ] **Step 4: Create and apply the first Alembic migration**

Run:

```bash
alembic revision --autogenerate -m "create initial content schema"
alembic upgrade head
```

Review the generated migration so all tables, indexes, foreign keys, uniqueness constraints, and publication checks are explicit.

- [ ] **Step 5: Run the schema tests and verify they pass**

Run: `pytest tests/db/test_schema.py -q`
Expected: PASS against SQLite.

**Done looks like:** The database can represent the approved profile, resume, organization, role, experience, project, metric, skill, certification, achievement, and external media-link data with relational constraints and migrations.

**How to check:** Run `alembic upgrade head`, `alembic downgrade base`, `alembic upgrade head`, and `pytest tests/db/test_schema.py -q` using SQLite.

- [ ] **Step 6: Commit**

```bash
git add app/db app/main.py tests/db pyproject.toml
git commit -m "feat: add career content schema and migrations"
```

### Task 3: Implementing publication rules and public content queries

**Files:**
- Create: `app/schemas/content.py`
- Create: `app/repositories/content.py`
- Create: `app/services/public_content.py`
- Create: `tests/services/test_public_content.py`

**Interfaces:**
- Produces `get_public_profile(db: Session) -> PublicProfile`.
- Produces `list_public_projects(db: Session, featured_only: bool = False) -> list[PublicProjectSummary]`.
- Produces `get_public_project(db: Session, slug: str) -> PublicProject | None`.
- Produces `PublicProject` and `PublicProfile` schemas that contain no draft, private, or internal fields.

- [ ] **Step 1: Write failing tests for publication filtering**

```python
def test_public_project_query_excludes_drafts_and_archived(db_session):
    create_project(db_session, slug="published", status="published")
    create_project(db_session, slug="draft", status="draft")
    create_project(db_session, slug="archived", status="archived")
    projects = list_public_projects(db_session)
    assert [project.slug for project in projects] == ["published"]
```

- [ ] **Step 2: Run the tests and verify they fail**

Run: `pytest tests/services/test_public_content.py -q`
Expected: FAIL because the public service and schemas do not exist.

- [ ] **Step 3: Implement typed repositories and public service functions**

Apply publication, visibility, scheduled-date, and ordering predicates inside repository queries. Map ORM objects into Pydantic public schemas so private administrative fields cannot leak through templates.

- [ ] **Step 4: Add profile and project edge-case tests**

Cover missing slugs, unpublished featured projects, empty optional relationships, malformed media URLs, and deterministic ordering by explicit display order then publication date.

- [ ] **Step 5: Run the tests and verify they pass**

Run: `pytest tests/services/test_public_content.py -q`
Expected: PASS.

**Done looks like:** All public content is retrieved through a single publication-aware service boundary, and tests prove drafts, archived records, private fields, and invalid visibility states are excluded.

**How to check:** Run the service test file and inspect the serialized `PublicProfile`/`PublicProject` output to confirm it contains only visitor-safe fields.

- [ ] **Step 6: Commit**

```bash
git add app/schemas/content.py app/repositories/content.py app/services/public_content.py tests/services/test_public_content.py
git commit -m "feat: enforce published public content queries"
```

### Task 4: Rendering the public profile, resume, and case studies

**Files:**
- Create: `app/routes/public.py`
- Create: `app/templates/base.html`
- Create: `app/templates/public/home.html`
- Create: `app/templates/public/project.html`
- Create: `app/templates/public/404.html`
- Modify: `app/main.py`
- Modify: `app/static/css/site.css`
- Create: `tests/routes/test_public_pages.py`

**Interfaces:**
- Produces `GET /` for the hybrid profile/resume home page.
- Produces `GET /projects/{slug}` for published case studies.
- Produces `GET /resume.pdf` for the versioned static resume asset when present.

- [ ] **Step 1: Write failing route tests**

```python
def test_home_page_contains_profile_and_featured_project(client, seeded_public_content):
    response = client.get("/")
    assert response.status_code == 200
    assert "Business Transformation" in response.text
    assert "Featured project" in response.text

def test_draft_project_is_not_public(client, seeded_public_content):
    response = client.get("/projects/draft-project")
    assert response.status_code == 404
```

- [ ] **Step 2: Run the tests and verify they fail**

Run: `pytest tests/routes/test_public_pages.py -q`
Expected: FAIL because the public router and templates do not exist.

- [ ] **Step 3: Implement the public routes and templates**

Render executive profile content first, followed by concise resume sections, measurable achievements, featured projects, and the contact/resume CTA. Use escaped Jinja output, semantic headings, accessible link labels, and stable slugs.

- [ ] **Step 4: Add placeholder sections**

Render only configured roadmap placeholders with exact labels such as “Case studies in progress”, “Career tools coming soon”, and “Insights coming soon”. Do not render draft resume fields or administrative notes.

- [ ] **Step 5: Add CSS and static resume handling**

Create a responsive, readable layout for recruiter scanning and serve the resume PDF as a static file with a clear 404 response if the asset is not installed.

- [ ] **Step 6: Run the tests and verify they pass**

Run: `pytest tests/routes/test_public_pages.py -q`
Expected: PASS.

**Done looks like:** An unauthenticated visitor can scan the profile, resume highlights, CTA, and featured transformation projects, then open a published case study at a stable URL.

**How to check:** Run the route tests and open `http://localhost:8000/` with `uvicorn app.main:create_app --factory --reload`; verify draft projects are inaccessible.

- [ ] **Step 7: Commit**

```bash
git add app/routes/public.py app/templates app/static app/main.py tests/routes/test_public_pages.py
git commit -m "feat: render public resume and case studies"
```

### Task 5: Adding secure admin authentication and content editing

**Files:**
- Create: `app/services/auth.py`
- Create: `app/routes/auth.py`
- Create: `app/routes/admin.py`
- Create: `app/schemas/auth.py`
- Create: `app/templates/auth/login.html`
- Create: `app/templates/admin/dashboard.html`
- Create: `app/templates/admin/project_form.html`
- Create: `tests/routes/test_admin.py`
- Modify: `app/main.py`
- Modify: `app/config.py`

**Interfaces:**
- Produces `POST /auth/login`, `POST /auth/logout`.
- Produces `GET /admin`, `GET /admin/projects/new`, `POST /admin/projects`.
- Produces `GET /admin/projects/{project_id}/edit`, `POST /admin/projects/{project_id}`.
- Produces `require_admin(request: Request) -> AdminUser`.
- Produces signed, server-side session-cookie authentication with password hashing.

- [ ] **Step 1: Write failing authentication and authorization tests**

```python
def test_admin_redirects_anonymous_user(client):
    response = client.get("/admin", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/auth/login"

def test_admin_can_create_draft_project(admin_client):
    response = admin_client.post(
        "/admin/projects",
        data={"title": "Transformation", "slug": "transformation", "publication_status": "draft"},
    )
    assert response.status_code == 303
```

- [ ] **Step 2: Run the tests and verify they fail**

Run: `pytest tests/routes/test_admin.py -q`
Expected: FAIL because authentication, admin routes, and templates do not exist.

- [ ] **Step 3: Implement password hashing and signed sessions**

Store only password hashes, use a supported password-hashing library, rotate the session on login, expire sessions, and set secure cookie flags according to environment. Require the admin identity on all draft, private, preview, and mutation routes.

- [ ] **Step 4: Implement validated admin project forms**

Use Pydantic form validation for required title/slug fields, HTTPS media URLs, publication-state transitions, date consistency, and metric values. Commit each valid mutation transactionally and return field-level errors without partial writes.

- [ ] **Step 5: Add CSRF protection and explicit failure responses**

Require a per-session CSRF token on state-changing form submissions and return a clear unsuccessful response for expired sessions, invalid CSRF, constraint failures, and unavailable databases.

- [ ] **Step 6: Run the tests and verify they pass**

Run: `pytest tests/routes/test_admin.py -q`
Expected: PASS.

**Done looks like:** Only the authenticated site owner can view drafts or mutate content; project create/edit/preview/publish/unpublish flows are transactional and validated.

**How to check:** Run the admin test file, then manually log in at `/auth/login`, create a draft, preview it while authenticated, publish it, and verify it appears publicly only after publication.

- [ ] **Step 7: Commit**

```bash
git add app/services/auth.py app/routes/auth.py app/routes/admin.py app/schemas/auth.py app/templates/auth app/templates/admin app/main.py app/config.py tests/routes/test_admin.py
git commit -m "feat: add authenticated content administration"
```

### Task 6: Implementing atomic public snapshots and database outage fallback

**Files:**
- Create: `app/services/snapshots.py`
- Create: `app/templates/snapshot/home.html`
- Create: `app/templates/snapshot/project.html`
- Create: `tests/services/test_snapshots.py`
- Create: `tests/routes/test_snapshot_fallback.py`
- Modify: `app/routes/public.py`
- Modify: `app/routes/admin.py`
- Modify: `app/config.py`

**Interfaces:**
- Produces `generate_public_snapshot(db: Session, destination: Path) -> SnapshotManifest`.
- Produces `load_snapshot_page(path: Path) -> str`.
- Produces `SnapshotManifest` containing generation timestamp, content version, profile path, project paths, and checksum.
- Produces a public-route fallback that catches only the expected database connectivity error, loads the last valid snapshot, and re-raises unexpected errors.

- [ ] **Step 1: Write failing snapshot tests**

```python
def test_failed_generation_does_not_replace_previous_snapshot(tmp_path, db_session):
    previous = write_valid_snapshot(tmp_path)
    make_generation_fail(db_session)
    with pytest.raises(SnapshotGenerationError):
        generate_public_snapshot(db_session, tmp_path)
    assert read_manifest(tmp_path).checksum == previous.checksum

def test_home_page_keeps_profile_visible_when_database_is_unavailable(client, valid_snapshot):
    disable_database(client)
    response = client.get("/")
    assert response.status_code == 200
    assert "Business Transformation" in response.text
    assert "Contact" in response.text
```

- [ ] **Step 2: Run the tests and verify they fail**

Run: `pytest tests/services/test_snapshots.py tests/routes/test_snapshot_fallback.py -q`
Expected: FAIL because snapshot generation and fallback behavior do not exist.

- [ ] **Step 3: Implement snapshot rendering and atomic publication**

Generate the profile first, then published resume/project pages, validate that the profile identity, headline, value proposition, CTA, and core resume content exist, write to a temporary directory, calculate a manifest checksum, and atomically replace the active snapshot only after all required outputs succeed.

- [ ] **Step 4: Implement database-error fallback**

When live public reads fail with a known database connectivity error, serve the active snapshot. Keep the profile route and profile content independently renderable. Do not convert admin database failures or unexpected programming errors into public snapshot responses.

- [ ] **Step 5: Add publish-triggered snapshot generation**

After a successful publication transaction, generate a new snapshot. If generation fails, preserve the prior snapshot and show the administrator an explicit failure state rather than reporting a successful publication-plus-snapshot operation.

- [ ] **Step 6: Run the tests and verify they pass**

Run: `pytest tests/services/test_snapshots.py tests/routes/test_snapshot_fallback.py -q`
Expected: PASS.

**Done looks like:** The profile remains visible during database downtime, a failed generation cannot destroy the last valid snapshot, and public project pages fall back to their last generated versions.

**How to check:** Run the snapshot tests, stop the local database container, request `/`, and verify the profile and CTA render; then restart the database and confirm live content resumes.

- [ ] **Step 7: Commit**

```bash
git add app/services/snapshots.py app/templates/snapshot app/routes app/config.py tests/services/test_snapshots.py tests/routes/test_snapshot_fallback.py
git commit -m "feat: add atomic public snapshot fallback"
```

### Task 7: Adding backup, restore, and recovery verification

**Files:**
- Create: `scripts/restore_verify.py`
- Create: `tests/operations/test_restore_verify.py`
- Create: `docs/operations/recovery.md`
- Modify: `docker-compose.yml`
- Modify: `app/config.py`

**Interfaces:**
- Produces `restore_database(backup_path: Path, target_database_url: str) -> None`.
- Produces `verify_restored_application(database_url: str, base_url: str) -> RecoveryReport`.
- Produces `RecoveryReport` with migration, connectivity, representative-read, public-page, admin-edit, snapshot-generation, duration, and failure fields.

- [ ] **Step 1: Write failing verification tests**

```python
def test_recovery_report_requires_all_checks_to_pass():
    report = RecoveryReport(
        migration=True,
        connectivity=True,
        representative_read=True,
        public_page=True,
        admin_edit=True,
        snapshot_generation=False,
        duration_seconds=12,
        failures=["snapshot generation failed"],
    )
    assert report.success is False
```

- [ ] **Step 2: Run the tests and verify they fail**

Run: `pytest tests/operations/test_restore_verify.py -q`
Expected: FAIL because the recovery script and report model do not exist.

- [ ] **Step 3: Implement isolated restore verification**

Restore a backup into an isolated PostgreSQL target, apply migrations, verify connectivity and representative published-project reads, run public-page checks, perform an authenticated admin edit/read-back, generate a snapshot, and record elapsed duration. Any failed check must produce a non-zero exit status.

- [ ] **Step 4: Document operational targets and commands**

Document RPO 24 hours, RTO 4 hours, backup retention assumptions, required environment variables, restore isolation requirements, and commands for:

```bash
python scripts/restore_verify.py --backup path/to/backup.dump --target-database "$RECOVERY_DATABASE_URL"
```

- [ ] **Step 5: Run the tests and verify they pass**

Run: `pytest tests/operations/test_restore_verify.py -q`
Expected: PASS.

**Done looks like:** A restore check proves migrations, database reads, public rendering, admin editing, and snapshot generation, reports duration, and fails loudly on any incomplete recovery.

**How to check:** Run the automated operation tests, then execute the documented verification command against an isolated PostgreSQL database and confirm a successful `RecoveryReport`.

- [ ] **Step 6: Commit**

```bash
git add scripts/restore_verify.py tests/operations docs/operations docker-compose.yml app/config.py
git commit -m "feat: add database recovery verification"
```

### Task 8: Deploying behind Nginx on an Azure Linux VM

**Files:**
- Create: `deploy/nginx/career-platform.conf`
- Create: `deploy/systemd/career-platform.service`
- Create: `deploy/azure/README.md`
- Modify: `.env.example`
- Modify: `README.md`

**Interfaces:**
- Produces an Nginx virtual host that serves `/static/` and the active snapshot directory directly, proxies dynamic requests to `127.0.0.1:8000`, and forwards only required headers.
- Produces a systemd unit that starts Uvicorn with `app.main:create_app --factory`, restarts on failure, loads an environment file, and runs as a non-root service user.
- Produces an Azure deployment runbook covering VM hardening, managed PostgreSQL connectivity, DNS, TLS, health checks, migrations, deployment, rollback, and snapshot permissions.

- [ ] **Step 1: Write deployment configuration checks**

```python
def test_nginx_config_serves_snapshot_and_proxies_dynamic_requests():
    config = Path("deploy/nginx/career-platform.conf").read_text()
    assert "proxy_pass http://127.0.0.1:8000" in config
    assert "snapshot" in config
    assert "try_files" in config

def test_systemd_service_runs_uvicorn_without_root():
    unit = Path("deploy/systemd/career-platform.service").read_text()
    assert "User=career-platform" in unit
    assert "app.main:create_app" in unit
    assert "Restart=on-failure" in unit
```

- [ ] **Step 2: Run the checks and verify they fail**

Run: `pytest tests/operations/test_deployment_config.py -q`
Expected: FAIL because the Nginx and systemd files do not exist.

- [ ] **Step 3: Implement Nginx routing and static fallback**

Configure HTTPS termination, HTTP-to-HTTPS redirect, security headers, `/static/` and snapshot serving, dynamic proxying to Uvicorn, bounded request limits, and access/error logging. Ensure the profile snapshot remains reachable even when FastAPI cannot connect to PostgreSQL.

- [ ] **Step 4: Implement the systemd service**

Run Uvicorn on loopback only, load production secrets from a root-readable environment file, use a dedicated non-root user, set the working directory, restart on failure, and expose `/health` for local service checks.

- [ ] **Step 5: Document Azure deployment and rollback**

Document creation of an Azure Linux VM, NSG rules allowing only SSH from an operator range and HTTP/HTTPS publicly, managed PostgreSQL firewall/private connectivity, DNS, certificate issuance/renewal, least-privilege service accounts, snapshot-directory ownership, migration commands, health checks, and rollback to the previous application release and snapshot.

- [ ] **Step 6: Run the checks and verify they pass**

Run: `pytest tests/operations/test_deployment_config.py -q`
Expected: PASS.

**Done looks like:** The application can run as a non-root systemd service on an Azure Linux VM, Nginx serves static assets and the last-good snapshot independently, and dynamic requests reach FastAPI only through loopback.

**How to check:** On a staging VM, run `sudo nginx -t`, `sudo systemctl enable --now career-platform`, `curl -f http://127.0.0.1:8000/health`, and request the public HTTPS URL with PostgreSQL connectivity temporarily blocked to confirm the profile snapshot remains visible.

- [ ] **Step 7: Commit**

```bash
git add deploy .env.example README.md tests/operations/test_deployment_config.py
git commit -m "ops: deploy FastAPI behind Nginx on Azure VM"
```

### Task 9: Completing end-to-end acceptance coverage and operational documentation

**Files:**
- Create: `tests/e2e/test_public_and_admin_flow.py`
- Create: `tests/e2e/conftest.py`
- Create: `README.md`
- Modify: `docs/operations/recovery.md`
- Modify: `pyproject.toml`

**Interfaces:**
- Produces an end-to-end fixture that starts the application with SQLite and a temporary snapshot directory.
- Produces acceptance coverage for public browsing, admin editing, publication visibility, snapshot fallback, and static resume delivery.

- [ ] **Step 1: Write the full acceptance scenarios**

```python
def test_recruiter_flow_and_admin_publication(e2e_client):
    home = e2e_client.get("/")
    assert home.status_code == 200
    assert "Business Transformation" in home.text
    login = e2e_client.login()
    assert login.status_code in {200, 303}
    draft = e2e_client.create_project(slug="new-case-study")
    assert draft.status_code == 303
    assert e2e_client.get("/projects/new-case-study").status_code == 404
    assert e2e_client.publish_project("new-case-study").status_code == 303
    assert e2e_client.get("/projects/new-case-study").status_code == 200
```

- [ ] **Step 2: Run the acceptance tests and identify missing integration behavior**

Run: `pytest tests/e2e/test_public_and_admin_flow.py -q`
Expected: Any failure identifies a missing cross-boundary behavior from the earlier tasks.

- [ ] **Step 3: Implement only the integration fixes required by the failing scenarios**

Keep fixes within route wiring, fixture setup, error handling, and documentation; do not broaden the feature scope with opportunity tracking, uploads, networking, or multi-user workflows.

- [ ] **Step 4: Add local setup and production configuration documentation**

Document installation, SQLite test commands, Docker Compose startup, Azure VM/systemd deployment, Azure PostgreSQL environment variables, admin bootstrap, snapshot directory permissions, static resume placement, backup verification, and outage simulation.

- [ ] **Step 5: Run the complete available test suite**

Run: `pytest -q`
Expected: PASS with unit, integration, route, snapshot, operation, and end-to-end tests passing.

**Done looks like:** A new developer can start the service locally, create and publish a case study, verify that drafts are hidden, simulate a database outage while the profile remains visible, and run the recovery verification procedure from documented commands.

**How to check:** Follow `README.md` from a clean environment, run `docker compose up --build`, execute `pytest -q`, and manually verify the recruiter flow at the local URL.

- [ ] **Step 6: Commit**

```bash
git add tests/e2e README.md docs/operations/recovery.md pyproject.toml
git commit -m "test: document and verify complete career platform flow"
```

## Plan self-review

- **Spec coverage:** Visitor experience is covered by Tasks 3–4; placeholders by Task 4; relational data and project content by Task 2; server-only access by Tasks 2–5; outage profile fallback by Task 6; recovery checks and RPO/RTO by Task 7; security/error behavior by Task 5 and Task 6; Azure/Nginx/systemd deployment by Task 8; acceptance testing by Task 9.
- **Scope check:** Opportunity tracking, networking, tasks, uploads, and multi-user social features remain deferred as required by the spec.
- **Placeholder scan:** No implementation step is left as TBD, TODO, or “implement later”; each task identifies files, interfaces, test commands, expected results, and completion checks.
- **Type consistency:** Repository/service names and snapshot/authentication interfaces are defined before they are consumed by later tasks.
