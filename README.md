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
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

## Configuration

The project uses `.env.example` as a template. Set the following values in a local `.env` file when needed:

```env
ENVIRONMENT=development
DATABASE_URL=sqlite:///./career_platform.db
SECRET_KEY=change-me
SNAPSHOT_DIR=./snapshots
```

The production path is designed for Azure Linux VM + Nginx + systemd/Uvicorn with Azure Database for PostgreSQL, but the local codebase defaults to SQLite for rapid development and testing.

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
- Add Azure VM and Nginx deployment configuration
