# Railway + PostgreSQL Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move caelonk.me from the Azure VM (Nginx + Uvicorn + SQLite) to the existing Railway project (web service + PostgreSQL), carrying the live data across, then deallocate the VM and keep it as the rollback copy.

**Architecture:** The app keeps its shape. It gains a Postgres driver and normalizes Railway's `postgresql://` URL to SQLAlchemy's psycopg 3 driver, and production refuses the repo's public default secrets. A Dockerfile built from `uv.lock` runs Uvicorn on Railway's `$PORT` with proxy headers trusted, so generated URLs are `https://`. `railway.json` runs `alembic upgrade head` before each deploy and health-checks `/health`. A one-off script copies every table from the VM's SQLite file into the empty, migrated Postgres database and resets Postgres's id sequences. Snapshots go to a Railway volume at `/data`. Cloudflare DNS then moves from the VM's IP to Railway's custom-domain target.

**Tech Stack:** FastAPI + Uvicorn, SQLAlchemy 2.x, Alembic, psycopg 3 (`psycopg[binary]`), PostgreSQL (Railway), Docker (Railway build and local check), uv 0.12, Railway CLI, Cloudflare DNS, Azure CLI/portal (VM only).

**Spec:** The owner's request (2026-10-08): "Inspect my app and plan its move to Railway and PostgreSQL. The Railway project already exists with Postgres and a web service." Decisions made with the owner the same day: cut caelonk.me over to Railway; keep the VM **deallocated** afterwards as the rollback copy (don't delete it); the owner installs the Railway CLI and runs `railway login` before execution starts. Background: `docs/superpowers/specs/2026-09-15-personal-career-platform-design.md`, the VM as operated in `docs/superpowers/plans/2026-10-01-operate-the-vm.md`, and `docs/how-this-site-is-secured.md`.

## Execution status (updated 2026-10-10)

| Part | State |
|---|---|
| R0, R0b | Done (Railway CLI 5.64.1, logged in; Docker running) |
| Tasks 1–6 | Done on branch `railway-migration` (`dba4993`, `d41968c`, `aa519d9`, `3dccd86`, `df4ef2a`, `b6b4d75`), not merged |
| Whole-branch review | Done: ready to merge with fixes. Its one code finding is fixed in `776b3fa` (see Task 2) |
| R1 | Done; results under R1 |
| D1–D3 | Done early on 2026-10-10, before the first deploy; results under Data |
| R2 | Done 2026-10-10; results under R2 |
| R3 | Done 2026-10-10; results under R3 |
| R4, V1–V3, Domain, Shutdown, Record | Not done |

Changes from the plan as first written:

- The app service is named `career-platform`, not `web`.
- Work is on a branch, and **`main` is merged only after R2 and R3**, because `main` deploys to Railway automatically.
- The Railway database was migrated and loaded by hand before the first deploy, so R4's pre-deploy migration has nothing to do.

## Facts this plan relies on (checked 2026-10-08)

| Fact | Value | Consequence |
|---|---|---|
| Live site | `caelonk.me` and `www.caelonk.me`, Cloudflare DNS **A records → `52.162.50.66`, DNS only (gray cloud)**, Let's Encrypt cert on the VM's Nginx | Domain steps replace the A records with Railway's CNAME and TXT records |
| VM app | `/home/azureuser/career-platform`, systemd `career-platform`, `uvicorn … --workers 2` on `127.0.0.1:8000`, at commit `626e18c` | Same entry point on Railway: `app.main:create_app --factory` |
| Live data | SQLite `~/career-platform/career_platform.db` on the VM, at migration `20240917_initial_schema` (head). Row counts from the 2026-10-08 backup (`integrity_check` ok, every table identical to live): profiles 1, projects 4 (all published), project_metrics 6, media_links 0, organizations 3, roles 5, skills 39, project_skills 7, experiences 5, experience_skills 9, certifications 2, achievements 0, project_achievements 0 | Data steps copy it and compare row counts for **every** table. If the VM's counts have changed by D2, use the new numbers |
| VM backup | `~/backups/career_platform-20261008-214842Z.db` on the VM (102,400 bytes, mode 600), taken with SQLite's online backup API | A restore point on the VM's own disk. D2's laptop copy covers losing the VM |
| Postgres driver | **None installed.** `pyproject.toml` has no psycopg/psycopg2 | Without Task 1, a bare `postgresql://` URL makes SQLAlchemy import psycopg2 and the app crashes at boot |
| URL handling | `app/db/session.py` passes `DATABASE_URL` straight to `create_engine`; `migrations/env.py` overwrites `sqlalchemy.url` from settings | Task 1 normalizes in one place (`app/config.py`) and both use it |
| Migrations | One revision, `20240917_initial_schema`; `alembic.ini` has `script_location = migrations` | Pre-deploy runs `alembic upgrade head` on Railway |
| Dockerfile | Exists but copies only `pyproject.toml` and `app/`, uses `pip install -e .` (ignores `uv.lock`), hard-codes port 8000, no proxy headers | Task 5 rewrites it |
| Proxy | Railway terminates TLS and forwards plain HTTP. `base.html` uses `url_for('static', …)`, which builds **absolute** URLs from the request scheme | Without `--proxy-headers --forwarded-allow-ips '*'`, the stylesheet link is `http://…` on an `https://` page, the browser blocks it as mixed content, and the site renders unstyled |
| Secrets | `app/config.py` defaults `SECRET_KEY=development-secret-key` and a committed pbkdf2 hash for `ADMIN_PASSWORD`; the production check only rejects an **empty** key | Task 2 makes production refuse both defaults |
| Snapshots | Written to `SNAPSHOT_DIR` on every admin save; read only when the DB fails | Railway's filesystem is wiped on each deploy, so snapshots go on a volume at `/data` |
| `scripts/restore_verify.py` | A stub that checks only that its arguments are non-empty | Not used for verification here |
| Tools on the laptop | uv 0.12.20, Docker Desktop, Azure CLI, git, Python. **No Railway CLI, no `psql`** | The owner installs the Railway CLI first (R0). DB checks use Python |
| Campus network | LMU Wi-Fi blocks caelonk.me (`503` "Web Page Blocked") | Check the custom domain from a phone with Wi-Fi off |

## Global Constraints

- Every operational step names where it runs and who runs it: **Agent** (Laptop, Git Bash in `~/career-platform`), **Owner** (Laptop terminal, Railway dashboard, Cloudflare, Azure portal). Anything that reads production data or secrets (the VM's database or `.env`, Railway's database URLs) is an **Owner** step.
- Secrets are never printed, echoed, committed, or pasted into chat. Commands substitute them inline (`"$(…)"`) or let `railway run` inject them.
- The VM's SQLite file is never modified. It stays the rollback copy.
- No admin edits on the VM from the start of the Data steps until the domain cutover. Anything edited there in that window is lost.
- Railway services: the database is `Postgres` and the app is `career-platform` (confirmed in R1), in project `motivated-solace`, environment `production`.
- `main` deploys to Railway automatically. Nothing from `railway-migration` is merged or pushed to `main` until R2 and R3 are done and R2's variable names are checked.
- Code tasks follow TDD and commit separately. The full suite (`.venv/Scripts/python -m pytest -q`) passes after every task.
- Postgres-backed tests run only when `TEST_POSTGRES_URL` is set, and only against `localhost`, `127.0.0.1` or `::1`, because they drop the `public` schema.
- Stop at any **Check** that doesn't match and report the output before continuing.

## Review Focus

1. **Generated URLs use `http://` behind Railway's TLS proxy.** The page loads but the CSS and fonts are blocked as mixed content. Task 5 pins the Uvicorn flags in a config test and checks the rendered stylesheet href with `X-Forwarded-Proto: https` in the local container check.
2. **Postgres id sequences left at 1 after copying rows with explicit ids.** The site reads fine, but the first "Create project" in admin fails with a duplicate-key error. Task 4's Postgres test inserts a new project after the copy.
3. **The copy run twice, or run into a database that already has rows.** That leaves duplicates or a half-copied database. Task 4 refuses a non-empty target and tests the refusal.
4. **A Railway-style URL (`postgresql://` or `postgres://`) with no driver suffix.** SQLAlchemy picks psycopg2, which isn't installed, so the app crash-loops. Task 1 tests the normalization and that the psycopg dialect loads.
5. **A database password containing `%` (URL-encoded characters) passed through Alembic's ini-style config.** `ConfigParser` interpolation either raises or corrupts the URL, so pre-deploy migrations fail. Task 3 tests the round-trip.

---

## File Structure

| File | Responsibility | Task |
|---|---|---|
| `app/config.py` | Settings; `normalize_database_url()`; production refuses default secrets | 1, 2 |
| `app/db/session.py` | `engine_options()` picks SQLite or Postgres engine settings | 1 |
| `app/db/migrate.py` (new) | `alembic_config(url)`, `upgrade_to_head(url)`, `head_revision()`, `current_revision(url)` | 3 |
| `migrations/env.py` | Uses a URL passed in by `alembic_config()`, otherwise settings | 3 |
| `tests/postgres_support.py` (new) | `require_local_test_database(url)` safety guard | 3 |
| `tests/conftest.py` | `postgres_url` fixture (skips without `TEST_POSTGRES_URL`) | 3 |
| `scripts/copy_sqlite_to_postgres.py` (new) | `copy_database(source_url, target_url)` and CLI | 4 |
| `Dockerfile`, `.dockerignore` (new), `railway.json` (new) | Railway build, start, pre-deploy, and health check | 5 |
| `README.md`, `.env.example`, `docs/how-this-site-is-secured.md` | Docs for how it runs now | 6 |
| `pyproject.toml`, `uv.lock` | `psycopg[binary]` dependency | 1 |

---

## Prerequisites (Owner, before Task 1)

- [ ] **R0: Install and log in to the Railway CLI**
  - **Where:** Owner, Laptop
  - **Run:**
    ```bash
    npm install -g @railway/cli
    railway --version
    railway login
    railway whoami
    ```
  - **Check:** `railway --version` prints a version, and `railway whoami` prints the owner's account.
  - **Undo:** `npm uninstall -g @railway/cli`

- [ ] **R0b: Start Docker Desktop** (Tasks 3–5 use a local Postgres container and a local image build)
  - **Where:** Owner, Laptop
  - **Check:** `docker info --format '{{.ServerVersion}}'` prints a version.

---

### Task 1: Postgres driver and URL handling

**Files:**
- Modify: `pyproject.toml` (dependencies), `uv.lock`
- Modify: `app/config.py`
- Modify: `app/db/session.py`
- Test: `tests/test_config.py` (new), `tests/db/test_session.py` (new)

**Interfaces:**
- Produces: `app.config.normalize_database_url(url: str) -> str`; `Settings.database_url` is always normalized; `app.db.session.engine_options(database_url: str) -> dict`.

- [ ] **Step 1: Write the failing tests**

`tests/test_config.py`:
```python
from __future__ import annotations

import pytest

from app.config import Settings, normalize_database_url


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("postgresql://u:p@db.internal:5432/railway", "postgresql+psycopg://u:p@db.internal:5432/railway"),
        ("postgres://u:p@db.internal:5432/railway", "postgresql+psycopg://u:p@db.internal:5432/railway"),
        ("postgresql+psycopg://u:p@h/d", "postgresql+psycopg://u:p@h/d"),
        ("sqlite:///./career_platform.db", "sqlite:///./career_platform.db"),
    ],
)
def test_normalize_database_url(raw, expected):
    assert normalize_database_url(raw) == expected


def test_settings_normalize_database_url():
    settings = Settings(_env_file=None, database_url="postgresql://u:p@h:5432/d")
    assert settings.database_url == "postgresql+psycopg://u:p@h:5432/d"
```

`tests/db/test_session.py`:
```python
from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from app.db.session import engine_options


def test_sqlite_engine_options_keep_single_connection():
    options = engine_options("sqlite:///./x.db")
    assert options["poolclass"] is StaticPool
    assert options["connect_args"] == {"check_same_thread": False}


def test_postgres_engine_options_ping_before_use():
    assert engine_options("postgresql+psycopg://u:p@h/d") == {"pool_pre_ping": True}


def test_psycopg_dialect_is_installed():
    engine = create_engine("postgresql+psycopg://u:p@localhost/d", **engine_options("postgresql+psycopg://u:p@localhost/d"))
    assert engine.dialect.driver == "psycopg"
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv/Scripts/python -m pytest tests/test_config.py tests/db/test_session.py -q`
Expected: FAIL with `ImportError: cannot import name 'normalize_database_url'` and `cannot import name 'engine_options'`.

- [ ] **Step 3: Add the driver**

Run: `uv add "psycopg[binary]>=3.2,<4"`
Expected: `pyproject.toml` dependencies gain `"psycopg[binary]>=3.2,<4"`, and `uv.lock` is updated. Then `uv sync --extra dev` so `.venv` has it.

- [ ] **Step 4: Implement**

`app/config.py`: add the import `field_validator` next to `model_validator`, then add above `class Settings`:
```python
_POSTGRES_PREFIXES = ("postgres://", "postgresql://")


def normalize_database_url(url: str) -> str:
    """Point Postgres URLs at the psycopg 3 driver; Railway hands out bare postgresql:// URLs."""
    for prefix in _POSTGRES_PREFIXES:
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url[len(prefix):]
    return url
```
and inside `Settings`, after `model_config`:
```python
    @field_validator("database_url")
    @classmethod
    def normalize_database_url_field(cls, value: str) -> str:
        return normalize_database_url(value)
```

`app/db/session.py`: replace the `engine_kwargs` block and the `engine =` line with:
```python
def engine_options(database_url: str) -> dict:
    if database_url.startswith("sqlite"):
        return {"connect_args": {"check_same_thread": False}, "poolclass": StaticPool}
    return {"pool_pre_ping": True}


engine: Engine = create_engine(settings.database_url, **engine_options(settings.database_url))
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `.venv/Scripts/python -m pytest -q`
Expected: all pass (22 existing + 8 new).

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml uv.lock app/config.py app/db/session.py tests/test_config.py tests/db/test_session.py
git commit -m "feat: add psycopg driver and normalize Postgres database URLs"
```

---

### Task 2: Production refuses the repo's public default secrets

> **Added after review (`776b3fa`):** the check as written below only ran when `ENVIRONMENT` was exactly `production`, so a missing or mis-cased variable skipped it. `Settings.is_production` is now also true whenever Railway's own `RAILWAY_ENVIRONMENT_NAME` is present, `ENVIRONMENT` is trimmed and lower-cased, and the admin cookie's `Secure` flag uses `is_production`. Tests: `tests/test_config.py`, `tests/services/test_auth_cookie.py`.

**Files:**
- Modify: `app/config.py`
- Test: `tests/test_config.py`

**Interfaces:**
- Produces: `app.config.DEFAULT_SECRET_KEYS: frozenset[str]`, `app.config.DEFAULT_ADMIN_PASSWORD_HASH: str`. `Settings(environment="production", …)` raises `ValueError` (wrapped by pydantic as `ValidationError`) when either default is in use.

- [ ] **Step 1: Write the failing tests** (append to `tests/test_config.py`)

```python
from pydantic import ValidationError

from app.config import DEFAULT_ADMIN_PASSWORD_HASH

PRIVATE_HASH = "pbkdf2_sha256$200000$c2FsdA==$ZGlnZXN0"


@pytest.mark.parametrize("secret", ["", "development-secret-key", "change-me-in-development"])
def test_production_rejects_public_secret_keys(secret):
    with pytest.raises(ValidationError, match="SECRET_KEY"):
        Settings(_env_file=None, environment="production", secret_key=secret, admin_password=PRIVATE_HASH)


def test_production_rejects_default_admin_password_hash():
    with pytest.raises(ValidationError, match="ADMIN_PASSWORD"):
        Settings(_env_file=None, environment="production", secret_key="a-private-value", admin_password=DEFAULT_ADMIN_PASSWORD_HASH)


def test_production_accepts_private_values():
    settings = Settings(_env_file=None, environment="production", secret_key="a-private-value", admin_password=PRIVATE_HASH)
    assert settings.environment == "production"


def test_development_allows_defaults():
    assert Settings(_env_file=None, environment="development").secret_key == "development-secret-key"
```

- [ ] **Step 2: Run to verify they fail**

Run: `.venv/Scripts/python -m pytest tests/test_config.py -q`
Expected: FAIL. The import of `DEFAULT_ADMIN_PASSWORD_HASH` errors, and the default secret keys are accepted.

- [ ] **Step 3: Implement** in `app/config.py`

Add above `class Settings`:
```python
DEFAULT_SECRET_KEYS = frozenset({"development-secret-key", "change-me-in-development", "change-me"})
DEFAULT_ADMIN_PASSWORD_HASH = "pbkdf2_sha256$200000$Fvzz02RnT3msIEguSTqeKg==$2BYWgTJVHt0dFTiNHQ54vReZRxM4iAi4Ho6i791gvs4="
```
Change the `admin_password` field to `Field(default=DEFAULT_ADMIN_PASSWORD_HASH)`, and replace the validator body:
```python
    @model_validator(mode="after")
    def validate_production_settings(self):
        if self.environment != "production":
            return self
        if not self.secret_key.strip() or self.secret_key in DEFAULT_SECRET_KEYS:
            raise ValueError("SECRET_KEY must be set to a private value when ENVIRONMENT=production.")
        if self.admin_password == DEFAULT_ADMIN_PASSWORD_HASH:
            raise ValueError("ADMIN_PASSWORD must be set to your own password hash when ENVIRONMENT=production.")
        return self
```

- [ ] **Step 4: Run the full suite**

Run: `.venv/Scripts/python -m pytest -q`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add app/config.py tests/test_config.py
git commit -m "feat: refuse public default secrets when ENVIRONMENT=production"
```

---

### Task 3: Migrations callable from code, and a local Postgres test harness

**Files:**
- Create: `app/db/migrate.py`
- Modify: `migrations/env.py:14`
- Create: `tests/postgres_support.py`
- Modify: `tests/conftest.py` (add fixture)
- Test: `tests/db/test_migrate.py` (new), `tests/db/test_postgres.py` (new)

**Interfaces:**
- Consumes: `normalize_database_url` (Task 1).
- Produces: `app.db.migrate.alembic_config(database_url: str) -> alembic.config.Config`, `upgrade_to_head(database_url: str) -> None`, `head_revision() -> str`, `current_revision(database_url: str) -> str | None`; `tests.postgres_support.require_local_test_database(url: str) -> str` (returns the normalized URL or raises `ValueError`); pytest fixture `postgres_url` (a normalized URL to an **empty** local database, or skip).

- [ ] **Step 1: Write the failing tests**

`tests/db/test_migrate.py`:
```python
from __future__ import annotations

import pytest
from sqlalchemy import create_engine, inspect

from app.db.migrate import alembic_config, current_revision, head_revision, upgrade_to_head
from tests.postgres_support import require_local_test_database


def test_alembic_config_round_trips_percent_encoded_passwords():
    url = "postgresql+psycopg://user:p%40ss%25word@localhost:5432/db"
    assert alembic_config(url).get_main_option("sqlalchemy.url") == url


def test_upgrade_to_head_on_sqlite(tmp_path):
    url = f"sqlite:///{tmp_path / 'm.db'}"
    assert current_revision(url) is None
    upgrade_to_head(url)
    assert current_revision(url) == head_revision() == "20240917_initial_schema"
    assert "projects" in inspect(create_engine(url)).get_table_names()


@pytest.mark.parametrize("host", ["localhost", "127.0.0.1"])
def test_local_test_database_is_allowed(host):
    assert require_local_test_database(f"postgresql://u:p@{host}:5432/d").startswith("postgresql+psycopg://")


def test_remote_test_database_is_refused():
    with pytest.raises(ValueError, match="local"):
        require_local_test_database("postgresql://u:p@monorail.proxy.rlwy.net:41234/railway")
```

`tests/db/test_postgres.py`:
```python
from __future__ import annotations

from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import session as db_session_module
from app.db.migrate import upgrade_to_head
from app.db.models import Base, Profile, Project
from app.main import create_app


def test_migrations_match_models_on_postgres(postgres_url):
    upgrade_to_head(postgres_url)
    engine = create_engine(postgres_url)
    with engine.connect() as connection:
        diff = compare_metadata(MigrationContext.configure(connection), Base.metadata)
    engine.dispose()
    assert diff == []


def test_public_pages_render_from_postgres(postgres_url):
    upgrade_to_head(postgres_url)
    engine = create_engine(postgres_url)
    db_session_module.engine = engine
    db_session_module.SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)
    with db_session_module.SessionLocal() as session:
        session.add(Profile(name="Alex Jordan", headline="Builder · Systems", summary="Builds things.", email="alex@example.com"))
        session.add(Project(title="Featured project", slug="featured-project", summary="A story.", publication_status="published", featured=True, display_order=1))
        session.add(Project(title="Draft", slug="draft", summary="Hidden.", publication_status="draft", display_order=2))
        session.commit()
    with TestClient(create_app()) as client:
        assert client.get("/").status_code == 200
        assert "Featured project" in client.get("/projects/featured-project").text
        assert client.get("/projects/draft").status_code == 404
    engine.dispose()
```

- [ ] **Step 2: Run to verify they fail**

Run: `.venv/Scripts/python -m pytest tests/db/test_migrate.py tests/db/test_postgres.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.db.migrate'` (and `tests.postgres_support`).

- [ ] **Step 3: Implement `app/db/migrate.py`**

```python
from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine

from app.config import normalize_database_url

REPO_ROOT = Path(__file__).resolve().parents[2]


def alembic_config(database_url: str) -> Config:
    """Alembic config for this repo, pointed at database_url instead of the settings URL."""
    config = Config(str(REPO_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(REPO_ROOT / "migrations"))
    # Config values go through ConfigParser interpolation, so a literal % (URL-encoded passwords) must be doubled.
    config.set_main_option("sqlalchemy.url", normalize_database_url(database_url).replace("%", "%%"))
    config.attributes["database_url"] = normalize_database_url(database_url)
    return config


def upgrade_to_head(database_url: str) -> None:
    command.upgrade(alembic_config(database_url), "head")


def head_revision() -> str:
    return ScriptDirectory.from_config(alembic_config("sqlite://")).get_current_head()


def current_revision(database_url: str) -> str | None:
    engine = create_engine(normalize_database_url(database_url))
    try:
        with engine.connect() as connection:
            return MigrationContext.configure(connection).get_current_revision()
    finally:
        engine.dispose()
```

- [ ] **Step 4: Make `migrations/env.py` honor the passed URL**

Replace line 14 (`config.set_main_option("sqlalchemy.url", get_settings().database_url)`) with:
```python
database_url = config.attributes.get("database_url") or get_settings().database_url
config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))
```

- [ ] **Step 5: Implement the guard and fixture**

`tests/postgres_support.py`:
```python
from __future__ import annotations

from sqlalchemy.engine import make_url

from app.config import normalize_database_url

LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}


def require_local_test_database(url: str) -> str:
    """Postgres tests drop the public schema, so they may only touch a local throwaway database."""
    normalized = normalize_database_url(url)
    if make_url(normalized).host not in LOCAL_HOSTS:
        raise ValueError("TEST_POSTGRES_URL must point at a local throwaway database (localhost); these tests wipe it.")
    return normalized
```

Append to `tests/conftest.py` (and add `import os`, `from sqlalchemy import text`, and `from tests.postgres_support import require_local_test_database` to its imports):
```python
@pytest.fixture
def postgres_url():
    raw = os.environ.get("TEST_POSTGRES_URL")
    if not raw:
        pytest.skip("TEST_POSTGRES_URL is not set")
    url = require_local_test_database(raw)
    engine = create_engine(url)
    with engine.begin() as connection:
        connection.execute(text("DROP SCHEMA public CASCADE"))
        connection.execute(text("CREATE SCHEMA public"))
    engine.dispose()
    return url
```

- [ ] **Step 6: Run the SQLite-only suite**

Run: `.venv/Scripts/python -m pytest -q`
Expected: all pass; the 2 tests in `tests/db/test_postgres.py` report **skipped**.

- [ ] **Step 7: Run against a local Postgres**

Run:
```bash
docker compose --profile postgres up -d postgres
TEST_POSTGRES_URL=postgresql://career_platform:career_platform@localhost:5432/career_platform .venv/Scripts/python -m pytest -q
```
Expected: all pass, **0 skipped**. If `test_migrations_match_models_on_postgres` reports a diff, the migration and the models disagree on Postgres. Print `diff`, fix the model or add a migration so they match, and don't weaken the assertion.

- [ ] **Step 8: Commit**

```bash
git add app/db/migrate.py migrations/env.py tests/postgres_support.py tests/conftest.py tests/db/test_migrate.py tests/db/test_postgres.py
git commit -m "feat: run migrations from code and test schema and pages on Postgres"
```

---

### Task 4: SQLite → Postgres copy script

**Files:**
- Create: `scripts/copy_sqlite_to_postgres.py`
- Test: `tests/operations/test_copy_sqlite_to_postgres.py` (new)

**Interfaces:**
- Consumes: `upgrade_to_head`, `head_revision`, `current_revision` (Task 3); `normalize_database_url` (Task 1); fixture `postgres_url` (Task 3).
- Produces: `scripts.copy_sqlite_to_postgres.copy_database(source_url: str, target_url: str) -> dict[str, int]` (table name → rows copied); `CopyError(RuntimeError)`; CLI `python -m scripts.copy_sqlite_to_postgres --source <path.db> [--target-env DATABASE_PUBLIC_URL]`.

- [ ] **Step 1: Write the failing tests**

`tests/operations/test_copy_sqlite_to_postgres.py`:
```python
from __future__ import annotations

from datetime import datetime

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.db.migrate import upgrade_to_head
from app.db.models import Base, MediaLink, Organization, Profile, Project, ProjectMetric, Role, Skill
from scripts.copy_sqlite_to_postgres import CopyError, copy_database

CREATED = datetime(2026, 9, 29, 21, 53, 49, 508812)


def make_source(path) -> str:
    url = f"sqlite:///{path}"
    engine = create_engine(url)
    Base.metadata.create_all(engine)
    with Session(engine) as s:
        org = Organization(id=7, name="LMU ITS", created_at=CREATED)
        role = Role(id=3, name="ITS Student Manager", created_at=CREATED)
        skill = Skill(id=5, name="ServiceNow", created_at=CREATED)
        s.add_all([org, role, skill])
        s.add(Profile(id=1, name="Caelon King", headline="H", summary="S", email="c@example.com", created_at=CREATED, updated_at=CREATED))
        project = Project(id=4, title="Dispatch", slug="dispatch", summary="S", publication_status="published", featured=True,
                          organization_id=7, role_id=3, display_order=1, created_at=CREATED, updated_at=CREATED)
        project.skills.append(skill)
        s.add(project)
        s.add(ProjectMetric(id=9, project_id=4, label="Users supported", value="10,000"))
        s.add(MediaLink(id=2, project_id=4, label="Demo", url="https://example.com"))
        s.commit()
    engine.dispose()
    return url


def migrated_sqlite_target(path) -> str:
    url = f"sqlite:///{path}"
    upgrade_to_head(url)
    return url


def test_copies_every_table_with_values_intact(tmp_path):
    counts = copy_database(make_source(tmp_path / "src.db"), migrated_sqlite_target(tmp_path / "dst.db"))
    assert counts["projects"] == 1 and counts["project_skills"] == 1 and counts["media_links"] == 1
    engine = create_engine(f"sqlite:///{tmp_path / 'dst.db'}")
    with Session(engine) as s:
        project = s.get(Project, 4)
        assert project.featured is True
        assert project.created_at == CREATED
        assert project.organization.name == "LMU ITS"
        assert [skill.name for skill in project.skills] == ["ServiceNow"]


def test_refuses_target_that_already_has_rows(tmp_path):
    source = make_source(tmp_path / "src.db")
    target = migrated_sqlite_target(tmp_path / "dst.db")
    copy_database(source, target)
    with pytest.raises(CopyError, match="not empty"):
        copy_database(source, target)


def test_refuses_target_not_at_head(tmp_path):
    with pytest.raises(CopyError, match="alembic upgrade head"):
        copy_database(make_source(tmp_path / "src.db"), f"sqlite:///{tmp_path / 'blank.db'}")


def test_postgres_copy_resets_id_sequences(tmp_path, postgres_url):
    upgrade_to_head(postgres_url)
    counts = copy_database(make_source(tmp_path / "src.db"), postgres_url)
    assert counts["profiles"] == 1
    engine = create_engine(postgres_url)
    with Session(engine) as s:
        s.add(Project(title="New", slug="new", summary="S", publication_status="draft", display_order=2))
        s.add(Organization(name="Another org"))
        s.commit()
        assert s.scalar(select(func.max(Project.id))) == 5
        assert s.scalar(select(Organization.id).where(Organization.name == "Another org")) == 8
    engine.dispose()
```

- [ ] **Step 2: Run to verify they fail**

Run: `.venv/Scripts/python -m pytest tests/operations/test_copy_sqlite_to_postgres.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'scripts.copy_sqlite_to_postgres'`.

- [ ] **Step 3: Implement `scripts/copy_sqlite_to_postgres.py`**

```python
"""Copy every content table from a SQLite file into an empty, migrated database (Railway Postgres)."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from sqlalchemy import Integer, create_engine, func, select, text
from sqlalchemy.engine import make_url

from app.config import normalize_database_url
from app.db.migrate import current_revision, head_revision
from app.db.models import Base


class CopyError(RuntimeError):
    pass


def _reset_postgres_sequences(connection) -> None:
    """Rows were inserted with explicit ids, so move each serial sequence past the highest id."""
    for table in Base.metadata.sorted_tables:
        id_column = table.columns.get("id")
        if id_column is None or not isinstance(id_column.type, Integer):
            continue
        connection.execute(
            text(
                f"SELECT setval(pg_get_serial_sequence('{table.name}', 'id'), "
                f"COALESCE((SELECT MAX(id) FROM {table.name}), 1), "
                f"(SELECT MAX(id) FROM {table.name}) IS NOT NULL)"
            )
        )


def copy_database(source_url: str, target_url: str) -> dict[str, int]:
    source_url, target_url = normalize_database_url(source_url), normalize_database_url(target_url)
    if current_revision(target_url) != head_revision():
        raise CopyError("Target schema is not at the latest migration; run `alembic upgrade head` against it first.")

    source = create_engine(source_url)
    target = create_engine(target_url)
    tables = Base.metadata.sorted_tables
    try:
        with target.connect() as connection:
            occupied = [t.name for t in tables if connection.scalar(select(func.count()).select_from(t))]
        if occupied:
            raise CopyError(f"Target is not empty ({', '.join(occupied)} already have rows); refusing to copy.")

        copied: dict[str, int] = {}
        with source.connect() as reader, target.begin() as writer:
            for table in tables:
                rows = [dict(row) for row in reader.execute(select(table)).mappings()]
                if rows:
                    writer.execute(table.insert(), rows)
                copied[table.name] = len(rows)
            if writer.dialect.name == "postgresql":
                _reset_postgres_sequences(writer)

        with target.connect() as connection:
            for table in tables:
                landed = connection.scalar(select(func.count()).select_from(table))
                if landed != copied[table.name]:
                    raise CopyError(f"{table.name}: copied {copied[table.name]} rows but target has {landed}.")
        return copied
    finally:
        source.dispose()
        target.dispose()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True, help="Path to the SQLite file to copy from")
    parser.add_argument("--target-env", default="DATABASE_PUBLIC_URL", help="Environment variable holding the target URL")
    args = parser.parse_args()

    if not args.source.is_file():
        print(f"Source file not found: {args.source}", file=sys.stderr)
        return 1
    target_url = os.environ.get(args.target_env)
    if not target_url:
        print(f"{args.target_env} is not set; run this under `railway run --service Postgres`.", file=sys.stderr)
        return 1

    print("Target:", make_url(normalize_database_url(target_url)).render_as_string(hide_password=True))
    try:
        counts = copy_database(f"sqlite:///{args.source.resolve()}", target_url)
    except CopyError as error:
        print(f"Copy refused: {error}", file=sys.stderr)
        return 1
    for name, count in counts.items():
        print(f"{name:24} {count}")
    print("Copy complete; row counts match.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run the tests (SQLite, then Postgres)**

Run:
```bash
.venv/Scripts/python -m pytest -q
TEST_POSTGRES_URL=postgresql://career_platform:career_platform@localhost:5432/career_platform .venv/Scripts/python -m pytest -q
```
Expected: the first run passes with 3 tests skipped (2 in `test_postgres.py`, 1 sequence test). The second run passes with 0 skipped.

- [ ] **Step 5: Commit**

```bash
git add scripts/copy_sqlite_to_postgres.py tests/operations/test_copy_sqlite_to_postgres.py
git commit -m "feat: add SQLite-to-Postgres copy script with sequence reset"
```

---

### Task 5: Container and Railway config

**Files:**
- Modify: `Dockerfile` (rewrite)
- Create: `.dockerignore`, `railway.json`
- Test: `tests/operations/test_deployment_config.py` (append)

**Interfaces:**
- Consumes: `alembic.ini` + `migrations/` (Task 3) inside the image, the `psycopg` dependency (Task 1).
- Produces: an image that listens on `$PORT`, trusts `X-Forwarded-*`, and has `alembic` on `PATH`; Railway runs `alembic upgrade head` before each deploy and checks `/health`.

- [ ] **Step 1: Write the failing tests** (append to `tests/operations/test_deployment_config.py`; add `import json` at the top)

```python
def test_dockerfile_serves_on_railway_port_behind_proxy():
    dockerfile = Path("Dockerfile").read_text()
    assert "uv sync --locked --no-dev" in dockerfile
    assert "${PORT:-8000}" in dockerfile
    assert "--proxy-headers" in dockerfile
    assert "--forwarded-allow-ips" in dockerfile
    for path in ("alembic.ini", "migrations", "scripts"):
        assert f"COPY {path}" in dockerfile


def test_railway_config_migrates_before_deploy_and_health_checks():
    config = json.loads(Path("railway.json").read_text())
    assert config["build"]["builder"] == "DOCKERFILE"
    assert config["deploy"]["preDeployCommand"] == "alembic upgrade head"
    assert config["deploy"]["healthcheckPath"] == "/health"


def test_dockerignore_keeps_secrets_and_local_data_out_of_the_image():
    ignored = Path(".dockerignore").read_text().splitlines()
    for entry in (".env", "*.db", ".venv", "snapshots"):
        assert entry in ignored
```

- [ ] **Step 2: Run to verify they fail**

Run: `.venv/Scripts/python -m pytest tests/operations/test_deployment_config.py -q`
Expected: 3 FAIL (no `${PORT:-8000}`, no `railway.json`, no `.dockerignore`).

- [ ] **Step 3: Write the files**

`Dockerfile` (the uv image tag matches the laptop's `uv --version`, 0.12.20):
```dockerfile
FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.12.20 /uv /uvx /bin/

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-install-project

COPY app ./app
COPY scripts ./scripts
COPY migrations ./migrations
COPY alembic.ini ./
RUN uv sync --locked --no-dev

EXPOSE 8000

# Railway sets PORT and terminates TLS in front of the container; trusting its
# X-Forwarded-Proto keeps url_for() links https:// so CSS and fonts aren't blocked.
CMD ["sh", "-c", "exec uvicorn app.main:create_app --factory --host 0.0.0.0 --port ${PORT:-8000} --workers 2 --proxy-headers --forwarded-allow-ips '*'"]
```

`.dockerignore`:
```
.env
*.db
.venv
snapshots
.git
.pytest_cache
__pycache__
*.egg-info
docs
.impeccable
.superpowers
```

`railway.json`:
```json
{
  "$schema": "https://railway.com/railway.schema.json",
  "build": {
    "builder": "DOCKERFILE",
    "dockerfilePath": "Dockerfile"
  },
  "deploy": {
    "preDeployCommand": "alembic upgrade head",
    "healthcheckPath": "/health",
    "healthcheckTimeout": 120,
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 5
  }
}
```

- [ ] **Step 4: Run the suite**

Run: `.venv/Scripts/python -m pytest -q`
Expected: all pass.

- [ ] **Step 5: Local container check against the compose Postgres** (Review Focus 1)

Run:
```bash
docker compose --profile postgres up -d postgres
docker build -t career-platform:railway .
NET=$(docker inspect career-platform-postgres --format '{{range $k, $v := .NetworkSettings.Networks}}{{$k}}{{end}}')
DB=postgresql://career_platform:career_platform@career-platform-postgres:5432/career_platform
docker run --rm --network "$NET" -e DATABASE_URL=$DB career-platform:railway alembic upgrade head
docker run -d --name cp-railway-check --network "$NET" -p 8080:8080 -e PORT=8080 -e DATABASE_URL=$DB \
  -e ENVIRONMENT=production -e SECRET_KEY=local-check-only -e ADMIN_PASSWORD='pbkdf2_sha256$1$c2FsdA==$ZGlnZXN0' \
  -e SNAPSHOT_DIR=/tmp/snapshots career-platform:railway
sleep 4
curl -s -o /dev/null -w "health %{http_code}\n" http://127.0.0.1:8080/health
curl -s -H "X-Forwarded-Proto: https" http://127.0.0.1:8080/ | grep -o 'href="[^"]*site.css"'
docker logs cp-railway-check 2>&1 | tail -5
docker rm -f cp-railway-check
```
**Check:** `health 200`. The stylesheet href starts with **`https://`**. The logs show Uvicorn on `0.0.0.0:8080` with no tracebacks. The home page renders with no profile, since the database is empty. If the href is `http://`, the proxy flags aren't taking effect, so don't continue.

- [ ] **Step 6: Commit**

```bash
git add Dockerfile .dockerignore railway.json tests/operations/test_deployment_config.py
git commit -m "feat: build for Railway with uv lock, PORT, proxy headers, and pre-deploy migrations"
```

Don't push to `main` here. `main` deploys automatically, and the service has no secrets set until R2. The merge is R4.

---

### Task 6: Docs for how the site runs now

**Files:**
- Modify: `README.md` (Local development step 4, Configuration, the "production path" paragraph, Next milestones)
- Modify: `.env.example`
- Modify: `docs/how-this-site-is-secured.md` (top of file)

- [ ] **Step 1: README**
  - Step 4's command becomes `uvicorn app.main:create_app --factory --host 0.0.0.0 --port 8000 --reload` (the existing `app.main:app` doesn't exist).
  - Replace the "production path" paragraph with: "Production runs on Railway: the `career-platform` service builds `Dockerfile` (see `railway.json`), runs `alembic upgrade head` before each deploy, and reads `DATABASE_URL` from the Railway Postgres service. `ENVIRONMENT=production` refuses the repository's default `SECRET_KEY` and admin password hash. Snapshots live on a Railway volume at `/data/snapshots`. The Azure VM is deallocated and kept as a rollback copy."
  - Add a "Postgres tests" subsection: `docker compose --profile postgres up -d postgres`, then `TEST_POSTGRES_URL=postgresql://career_platform:career_platform@localhost:5432/career_platform pytest -q`, with a note that these tests wipe that database's `public` schema.
  - Remove the "Add Azure VM and Nginx deployment configuration" milestone.
- [ ] **Step 2: `.env.example`** gains a commented line: `# ADMIN_PASSWORD=<pbkdf2 hash from app.services.auth.hash_password>; required when ENVIRONMENT=production`.
- [ ] **Step 3: `docs/how-this-site-is-secured.md`** gets a first-line note: "> Describes the Azure VM deployment, which served caelonk.me until <cutover date>. Since then the site runs on Railway; see the Railway migration plan." (The date is filled in at Domain 3.)
- [ ] **Step 4: Run the suite and commit**

```bash
.venv/Scripts/python -m pytest -q
git add README.md .env.example docs/how-this-site-is-secured.md
git commit -m "docs: describe the Railway deployment"
```

---

## Railway setup

- [x] **R1: Link and inspect the existing project**
  - **Where:** Agent, Laptop
  - **Run:** `railway link --project motivated-solace --environment production`, `railway status --json`, `railway deployment list --service career-platform --json`, and variable **names** only for both services.

  **Results (2026-10-08, re-checked 2026-10-10):**

  | Check | Actual |
  |---|---|
  | Project / environment | `motivated-solace` / `production`, linked in this folder |
  | App service | `career-platform`; source GitHub `caelonk/career-platform`, branch `main`; deploys on every push |
  | Database service | `Postgres` (image `postgres-ssl:18`, server 18.6), running, with its own volume |
  | App variables | Only `DATABASE_URL`, equal to the Postgres service's private address (port 5432, database `railway`); whether it's a `${{…}}` reference isn't visible from the CLI |
  | Railway-provided variables | `RAILWAY_ENVIRONMENT_NAME=production` is present on the app service |
  | Postgres variables | `DATABASE_URL` and `DATABASE_PUBLIC_URL` both present |
  | App deploys | 4, all **failed** at build on 2026-10-08 (commits `626e18c`, `ae8b4f5`, `aa5bc31`): `error: package directory 'scripts' does not exist`, from the old Dockerfile. Fixed by Task 5 once merged |
  | Domains / app volume | None |

- [x] **R2: Set the app service's variables**
  - **Where:** Laptop, Git Bash in `~/career-platform`. The Agent sets the three non-secret values and the new `SECRET_KEY`. The **Owner** sets `ADMIN_PASSWORD`, because that command reads the VM's `.env`. Secrets go in through stdin and command output is discarded, so nothing is printed.
  - **Run (Agent):**
    ```bash
    railway variable set 'DATABASE_URL=${{Postgres.DATABASE_URL}}' --service career-platform --skip-deploys > /dev/null && echo "DATABASE_URL set"
    railway variable set ENVIRONMENT=production --service career-platform --skip-deploys > /dev/null && echo "ENVIRONMENT set"
    MSYS_NO_PATHCONV=1 railway variable set SNAPSHOT_DIR=/data/snapshots --service career-platform --skip-deploys > /dev/null && echo "SNAPSHOT_DIR set"
    .venv/Scripts/python -c 'import secrets; print(secrets.token_urlsafe(48), end="")' | railway variable set SECRET_KEY --stdin --service career-platform --skip-deploys > /dev/null && echo "SECRET_KEY set"
    ```
  - **Run (Owner):**
    ```bash
    ssh -i ~/.ssh/isba4775_azure azureuser@52.162.50.66 "grep '^ADMIN_PASSWORD=' ~/career-platform/.env | cut -d= -f2-" | tr -d '\r\n' | railway variable set ADMIN_PASSWORD --stdin --service career-platform --skip-deploys > /dev/null && echo "ADMIN_PASSWORD set"
    ```
  - **Why:** `${{Postgres.DATABASE_URL}}` is a Railway reference over the private network, and it follows the database if its password changes. `SECRET_KEY` is new, so existing admin sessions end. `ADMIN_PASSWORD` reuses the VM's hash, so the admin password stays the same. `--skip-deploys` stops each change from starting another build of the old Dockerfile on `main`. The VM must be running for the `ssh`.
  - **Check:** `railway variables --service career-platform --kv | cut -d= -f1 | grep -v '^RAILWAY_'` lists exactly `ADMIN_PASSWORD`, `DATABASE_URL`, `ENVIRONMENT`, `SECRET_KEY`, `SNAPSHOT_DIR`. A check that prints only yes/no confirms `ENVIRONMENT` is exactly `production`, `ADMIN_PASSWORD` starts with `pbkdf2_sha256$` and is not the repository default, and `SECRET_KEY` is at least 32 characters.
  - **If `ADMIN_PASSWORD` comes out empty:** the VM's `.env` has no such line. The Owner sets a new one instead: `.venv/Scripts/python -c 'from app.services.auth import hash_password; import getpass; print(hash_password(getpass.getpass()), end="")' | railway variable set ADMIN_PASSWORD --stdin --service career-platform --skip-deploys > /dev/null`.
  - **Undo:** `railway variable delete <NAME> --service career-platform` (or delete in the dashboard).

  **Results (2026-10-10):** The Agent set `DATABASE_URL`, `ENVIRONMENT`, `SNAPSHOT_DIR` and `SECRET_KEY`; the Owner set `ADMIN_PASSWORD`. No deploy was triggered.

  | Check (yes/no only, values never printed) | Result |
  |---|---|
  | Names are exactly `ADMIN_PASSWORD`, `DATABASE_URL`, `ENVIRONMENT`, `SECRET_KEY`, `SNAPSHOT_DIR` | Pass |
  | `ENVIRONMENT` is exactly `production` | Pass |
  | `SNAPSHOT_DIR` is `/data/snapshots` | Pass (after the Git Bash path fix) |
  | `DATABASE_URL` resolves to the same private address as before | Pass |
  | `SECRET_KEY` is at least 32 characters, not a repository default, no stray whitespace | Pass |
  | `ADMIN_PASSWORD` is a four-part `pbkdf2_sha256` hash, not the repository default, no quotes or whitespace | Pass |

  Not yet proven: that the hash is the one your password matches. V2's admin login proves that.

- [x] **R3: Add a volume for snapshots**
  - **Where:** Agent, Laptop
  - **Run:** `MSYS_NO_PATHCONV=1 railway volume --service <career-platform service ID> add --mount-path /data` (the ID comes from `railway status --json`)
  - **Why the prefix:** Git Bash rewrites arguments that start with `/` into Windows paths. Without it, `/data/snapshots` was stored as `C:/Program Files/Git/data/snapshots` (caught by R2's check on 2026-10-10 and corrected).
  - **Check:** `railway volume list` shows one volume on `career-platform` mounted at `/data`. (Dashboard alternative: career-platform → Settings → Volumes → Add, mount path `/data`.)

  **Results (2026-10-10):**

  | Check | Actual | Result |
  |---|---|---|
  | CLI syntax (version 5.64.1) | `--service` belongs before `add` and must be the service **ID**. After `add` it's rejected; with the service name the CLI crashes without creating anything | Noted |
  | Volume | `career-platform-volume`, attached to `career-platform`, mount path `/data`, 0 MB of 500 MB, Ready | Pass |
  | Side effect | Adding the volume started a build of `main` (deployment `0679767a`). It failed at the same `scripts` step as before, as expected with the old Dockerfile | Expected |

- [ ] **R4: First deploy: merge `railway-migration` into `main`**
  - **Before:** R2 and R3 are done and R2's check passed. In the dashboard (Owner), career-platform → Settings → Deploy has **no custom Start Command**; one would replace the Dockerfile's command and drop the proxy flags.
  - **Where:** Owner decides when; Agent runs it on the Owner's word.
  - **Run:**
    ```bash
    git switch main && git merge --ff-only railway-migration && git push origin main
    railway deployment list --service career-platform | head -3
    railway logs --service career-platform --build -n 40
    railway logs --service career-platform --deployment -n 80
    railway domain --service career-platform          # prints (or creates) the *.up.railway.app address
    ```
  - **Check:**
    - The build succeeds and the deployment becomes **Active** (the `/health` check passed).
    - The log shows the **pre-deploy** phase running `alembic upgrade head` with `Context impl PostgresqlImpl`. There is **no** `Running upgrade` line, because the database is already at `20240917_initial_schema`. If no pre-deploy phase appears at all, `railway.json` was ignored (the CLI warns that this file format is deprecated); set the pre-deploy command and health check path in the service's settings instead.
    - Uvicorn reports `0.0.0.0:$PORT`.
    - `curl -s -o /dev/null -w "%{http_code}" https://<app>.up.railway.app/health` returns `200`, and the home page returns `200` with "Caelon King" (the data is already loaded).
    - Logging in at `/auth/login` as `admin` with the password `admin-password` is **rejected**. That is the repository's default; accepting it would mean R2's hash didn't take.
  - **If it stops at startup with `SECRET_KEY must be set…` or `ADMIN_PASSWORD must be set…`:** R2's values are missing or are the defaults. Fix them; Railway redeploys.
  - **Undo:** `git revert` the merge on `main` and push. caelonk.me is still on the VM at this point, so nothing public changes.

## Data (done early, 2026-10-10)

These ran before the first deploy, at the Owner's request. The schema was created by hand with the same migration the pre-deploy step runs.

- [x] **D1: Freeze admin edits on the VM**
  - **Where:** Owner
  - **Check:** No admin edits on caelonk.me from 2026-10-10 until Domain 3. The VM keeps serving the public site. Anything edited there now is not on Railway.

- [x] **D2: Copy the VM's database to the laptop and confirm it's intact**
  - **What ran:** On 2026-10-08 the VM database was backed up on the VM with SQLite's online backup API, and that backup was copied to `~/Downloads/railway-migration/career_platform-20261008-214842Z.db`.

  | Check | Result |
  |---|---|
  | VM live database vs VM backup, every row of all 14 tables | Identical (2026-10-08, again 2026-10-10 after the copy) |
  | SHA-256, VM backup vs laptop copy | Same (`b8c91c10…718c1a`) |
  | Laptop copy `integrity_check`, migration | `ok`, `20240917_initial_schema` |

- [x] **D3: Copy into Railway Postgres**
  - **Where:** Owner, Laptop. `railway run` injects the database address, so it never appears on screen. The Agent's attempt to write to the Railway database was stopped by its permission check, so the Owner ran both commands.
  - **What ran:**
    ```bash
    railway run --service Postgres '.venv\Scripts\python.exe' -I .superpowers/sdd/2026-10-08-railway-postgres-migration/railway_migrate.py   # alembic upgrade head
    railway run --service Postgres '.venv\Scripts\python.exe' -m scripts.copy_sqlite_to_postgres --source "C:/Users/caekn/Downloads/railway-migration/career_platform-20261008-214842Z.db" --target-env DATABASE_PUBLIC_URL
    ```
    On Windows `railway run` starts the program through `cmd`, so Python is called by its Windows path.
  - **Why `DATABASE_PUBLIC_URL`:** `DATABASE_URL` is a private address that only resolves inside Railway. The public address goes through Railway's TCP proxy and works from the laptop.

  **Results (2026-10-10):**

  | Check | Expected | Actual | Result |
  |---|---|---|---|
  | Railway database before | Empty | Postgres 18.6, no tables, no migration | Pass |
  | Migration | `None` → `20240917_initial_schema` | `before: None`, `after: 20240917_initial_schema` | Pass |
  | Copy target | Railway's public proxy host, password masked | As expected | Pass |
  | Copy output | 13 tables, `Copy complete; row counts match.` | As expected | Pass |
  | Laptop copy vs Railway, every row of all 13 tables (read through the app's models, hashed per table) | Identical | `ALL TABLES MATCH`, same migration version | Pass |

  | Table | VM rows | Railway rows | Table | VM rows | Railway rows |
  |---|---|---|---|---|---|
  | profiles | 1 | 1 | skills | 39 | 39 |
  | projects | 4 | 4 | project_skills | 7 | 7 |
  | project_metrics | 6 | 6 | experiences | 5 | 5 |
  | media_links | 0 | 0 | experience_skills | 9 | 9 |
  | organizations | 3 | 3 | certifications | 2 | 2 |
  | roles | 5 | 5 | achievements | 0 | 0 |
  | | | | project_achievements | 0 | 0 |

  Not checked on Railway itself yet: the id sequences. The script resets them and a test proves it against a local Postgres; V3 checks the real database.
  - **If this ever has to be repeated:** the script refuses a database that already has rows. Don't clear the Railway database without the Owner's decision.

## Verify on the Railway address (before touching DNS)

- [ ] **V1: Public pages, assets, and errors**
  - **Where:** Agent, Laptop. `U=https://<app>.up.railway.app`
  - **Run:**
    ```bash
    curl -s $U/ | grep -c "Caelon King"
    for s in technician-dispatch-dashboard third-party-vendor-risk-dashboard gdpr-ccpa-privacy-compliance-assessment legal-document-analyzer; do curl -s -o /dev/null -w "%{http_code} $s\n" $U/projects/$s; done
    curl -s $U/ | grep -o 'href="[^"]*site.css"'
    curl -s -o /dev/null -w "%{http_code} font\n" $U/static/fonts/schibsted-grotesk-latin-wght.woff2
    curl -s -o /dev/null -w "%{http_code} %{content_type} bad slug\n" -H "accept: text/html" $U/projects/bad-slug
    curl -s -o /dev/null -w "%{http_code} resume\n" $U/resume.pdf
    ```
  - **Check:** The name count is ≥ 2. All 4 project pages return `200`. The stylesheet href starts with `https://`. The font returns `200`. The bad slug returns `404 text/html`. The resume returns `200`. The page also looks right in a browser at desktop and phone widths.

- [ ] **V2: Admin login, save, and snapshot on the volume**
  - **Where:** Owner in a browser, then Agent
  - **Run:** Owner: log in at `$U/auth/login` with the usual admin password, open any project, and click **Save** without changes. Agent: `railway ssh --service career-platform -- ls -la /data/snapshots`
  - **Check:** Login lands on `/admin`, and the save redirects without an error. `/data/snapshots` contains `home.html`, `manifest.json` and `projects/`.

- [ ] **V3: New rows get fresh ids** (Review Focus 2, on the real database)
  - **Where:** Owner in a browser
  - **Run:** Admin → Create project with title `Sequence check`, slug `sequence-check`, status **Draft**, then Save.
  - **Check:** The save succeeds; a duplicate-key error here would mean the sequences weren't reset. Then edit it to **Archived**. Leave it archived; archived projects aren't public.

## Domain (Owner, in Railway and Cloudflare)

- [ ] **Domain 1: Add the custom domains in Railway**
  - **Where:** Owner, dashboard: career-platform → Settings → Networking → **+ Custom Domain**, once for `caelonk.me` and once for `www.caelonk.me`. (CLI: `railway domain caelonk.me --service career-platform`.)
  - **Check:** Railway shows, for each name, a `CNAME` target (`<something>.up.railway.app`) and a `TXT` verification record. Copy them exactly.

- [ ] **Domain 2: Repoint Cloudflare DNS**
  - **Where:** Owner, Cloudflare → caelonk.me → DNS
  - **Run:** Delete the `A @ 52.162.50.66` record and add `CNAME @ → <Railway target for caelonk.me>`, **DNS only (gray cloud)**. Cloudflare flattens a CNAME at the apex automatically. Do the same for `www` with its own target. Add both `TXT` records exactly as Railway shows them.
  - **Why gray cloud:** The site already runs DNS-only, and Railway then issues and renews the Let's Encrypt certificate itself. Turning the proxy on later also requires Cloudflare SSL mode **Full** (not Full strict).
  - **Undo (rollback):** Restore `A @ 52.162.50.66` and `A www 52.162.50.66` (DNS only), start the VM in the portal, and the old site is back within the 300 s TTL.

- [ ] **Domain 3: Confirm the cutover**
  - **Where:** Agent on the Laptop (not on campus Wi-Fi, or using `1.1.1.1`), and Owner on a phone with Wi-Fi off
  - **Run:**
    ```bash
    nslookup caelonk.me 1.1.1.1
    nslookup www.caelonk.me 1.1.1.1
    curl -sI https://caelonk.me | grep -i -E "^HTTP|server|x-railway"
    curl -s https://caelonk.me | grep -c "Caelon King"
    echo | openssl s_client -connect caelonk.me:443 -servername caelonk.me 2>/dev/null | openssl x509 -noout -issuer -enddate
    ```
  - **Check:** Neither name resolves to `52.162.50.66`. Railway shows both domains verified with a certificate issued. The response is `HTTP/2 200` with a `server: railway-edge` header or an `x-railway-*` header. The name count is ≥ 2. The issuer is Let's Encrypt and the expiry date is in the future. On the phone, `https://caelonk.me` and `https://www.caelonk.me` show the site with a padlock.

## Shutdown

- [ ] **S1: Deallocate the VM (kept as the rollback copy)**
  - **Where:** Owner, Azure portal → `vm-career-platform` → **Stop** (this deallocates it). Do it once Domain 3 has passed and the site has run on Railway for at least 24 hours with no errors in `railway logs`.
  - **Check:** `az vm show -d -g rg-career-platform -n vm-career-platform --query powerState -o tsv` prints `VM deallocated`. The disk and static IP remain, and so does the VM's `career_platform.db`, frozen at its 2026-10-08 state (unchanged since, as D2 records).
  - **Note:** While deallocated, the VM's certbot can't renew. Its certificate expires in early January 2027, which only matters if the VM is ever brought back as the live site.

## Record

- [ ] **Record 1:** Fill in a Results block under each operational step (R1–S1), like the earlier plans do: what ran, the expected value, the actual value, and pass or fail. Include the Railway project and service names, the deploy ID, the per-table copy counts, the V1 status codes, the resolved DNS answers, and the certificate issuer and expiry.
- [ ] **Record 2: Public-safety check before committing:** grep this file for `railway.internal`, `proxy.rlwy.net`, `postgresql://` URLs with credentials, `pbkdf2_sha256$` hashes other than the documented default, the laptop IP, subscription and tenant IDs, and emails. Expect no secrets. Hostnames shown as `<app>.up.railway.app` are fine.
- [ ] **Record 3:** Fill in the cutover date in `docs/how-this-site-is-secured.md` (Task 6, Step 3) and commit with the Results: `docs: record Railway migration results`.

## Rollback (any point after Domain 2)

1. Cloudflare: put back `A @` and `A www` → `52.162.50.66`, DNS only.
2. Azure portal: start `vm-career-platform`. systemd starts the app at boot; check `https://caelonk.me` from a phone.
3. Data written on Railway after D3 (admin edits) exists only in Railway Postgres. Before rolling back, the Owner decides whether to re-enter it on the VM.
