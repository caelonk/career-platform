# Career Platform

A database-driven personal resume and career platform for business transformation, digital transformation, IT strategy, and consulting roles.

## Status

This project is in the early implementation phase. The current codebase includes:

- FastAPI application foundation and health endpoint
- Environment-based configuration for local SQLite and production PostgreSQL targets
- Jinja-based template foundation and static CSS styling
- SQLAlchemy 2.x schema and Alembic migration for the public content model
- Database tests covering portfolio relationships and project metadata

## Local development

1. Create and activate a virtual environment.
2. Install dependencies:
   ```bash
   python -m pip install -e '.[dev]'
   ```
3. Run the health check:
   ```bash
   pytest -q
   ```
4. Start the app locally:
   ```bash
   uvicorn app.main:create_app --factory --host 0.0.0.0 --port 8000 --reload
   ```

### Postgres tests

Some tests only run against a real Postgres database. Start the local one, then point the tests at it:

```bash
docker compose --profile postgres up -d postgres
TEST_POSTGRES_URL=postgresql://career_platform:career_platform@localhost:5432/career_platform pytest -q
```

These tests wipe that database's `public` schema on every run, so they refuse any address that isn't on this machine. Without `TEST_POSTGRES_URL` they are skipped.

## Configuration

The project uses `.env.example` as a template. Set the following values in a local `.env` file when needed:

```env
ENVIRONMENT=development
DATABASE_URL=sqlite:///./career_platform.db
SECRET_KEY=change-me
SNAPSHOT_DIR=./snapshots
```

`ADMIN_PASSWORD` holds the admin password as a pbkdf2 hash (generate one with `app.services.auth.hash_password`). It is optional in development and required in production.

Production is set up on Railway: the `career-platform` service builds `Dockerfile` (see `railway.json`), runs `alembic upgrade head` before each deploy, and reads `DATABASE_URL` from the Railway Postgres service. `ENVIRONMENT=production` refuses the repository's default `SECRET_KEY` and admin password hash. Snapshots live on a Railway volume at `/data/snapshots`. The Azure VM that served the site before (Nginx + systemd/Uvicorn + SQLite) is kept, deallocated, as a rollback copy once the domain has moved. Local development and tests default to SQLite.

## Project structure

```text
app/
  config.py
  main.py
  static/
  templates/
app/db/
  models.py
  session.py
migrations/
  env.py
  versions/
tests/
  db/
```

## Next milestones

- Add publication-aware public content queries
- Render public profile, resume, and project pages
- Add authenticated admin editing and session-based login
- Add snapshot fallback and outage recovery checks
