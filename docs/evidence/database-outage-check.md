# Database outage check

What the home page does when its database stops and comes back. Run on the laptop on
2026-10-21 between 04:04 and 04:10 UTC (2026-10-20 evening, Pacific), against a local
PostgreSQL container, **not** against Railway. The live site hasn't been tested this way,
because stopping Railway's database would take `caelonk.me` down.

Code: commit `3c2117b` ("fix: return 503 with the profile kept when the database is down").
Automated tests for the same behavior: `tests/routes/test_database_outage.py`.

## Setup

| Part | Value |
|---|---|
| Database | `postgres:16-alpine` from `docker-compose.yml` (`docker compose --profile postgres up -d postgres`), migrated to `20240917_initial_schema` |
| Data | One profile ("Test Person") and one published project ("Local test project"), loaded by a throwaway script |
| App | `uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8011 --workers 2`, `DATABASE_URL=postgresql://…@localhost:5432/…` |
| Outage | `docker stop career-platform-postgres`, then `docker start` |

Each line below is one `curl` of `http://127.0.0.1:8011/`, counting the profile name,
the project title and the outage message in the returned HTML.

## Result

| Time (UTC) | State | HTTP | Time taken | Profile | Project | "Projects temporarily unavailable" |
|---|---|---|---|---|---|---|
| 04:09:50 | Healthy | **200** | 0.18 s | shown | shown | no |
| 04:09:50 | Healthy (second request) | **200** | 0.01 s | shown | shown | no |
| 04:09:51 | Database stopped | | | | | |
| 04:09:54 | Down | **503** | 3.1 s | shown | **not shown** | **yes** |
| 04:10:01 | Down, refresh | **503** | 6.1 s | shown | not shown | yes |
| | Project page while down | **503** | 6.0 s | | | |
| 04:10:08 | Database started, app **not** restarted | | | | | |
| 04:10:09 | Refresh | **200** | 0.04 s | shown | shown | no |
| 04:10:09 | Refresh | **200** | 0.01 s | shown | shown | no |
| | Project page after | **200** | | | | |

- The app log has 3 `Database read failed` entries, one per failed request.
- The profile during the outage came from the copy the app saved on the first healthy
  request (`profile.json` in `SNAPSHOT_DIR`), not from sample content. The old snapshot
  pages are no longer served to visitors.
- Recovery needed no restart: each request opens a new session, and `pool_pre_ping`
  replaces pooled connections that died with the database.

## Investigated failure: the outage first hung instead of returning 503

This is an application/database-dependency failure, found during this check, not staged.

| Step | What happened |
|---|---|
| **Symptom** | First run, 04:04 UTC: the healthy request returned 200, but after `docker stop`, `GET /` didn't answer at all. After two minutes the check was stopped. The app log showed no request line and no error. |
| **Checks** | `netstat` showed nothing listening on port 5432, so the database really was down. A standalone `psycopg.connect()` with no timeout to `127.0.0.1:5432` and to `localhost:5432` was still blocked after 60 s each. The same call with `connect_timeout=5` failed with `ConnectionTimeout` after 10.0 s (5 s for each of `localhost`'s two addresses). |
| **Diagnosis** | The app's Postgres engine (`app/db/session.py`) set no connect timeout, so each request waited on the connection attempt indefinitely and never reached the code that returns 503. The 503 code was right; the request never got there. |
| **Repair** | `connect_args={"connect_timeout": 3}` for Postgres engines, with a test in `tests/db/test_session.py` (watched failing first). |
| **Repeated check** | The run in the table above: 503 in 3.1 s and 6.1 s instead of hanging, then 200 after the database restarted. |

What isn't shown: whether Railway's private network would fail fast or hang when its
database stops. The timeout covers either case.
