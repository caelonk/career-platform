# Railway PostgreSQL credential rotation, 2026-10-24

Following Railway's post "Security disclosure: recommendation to rotate PostgreSQL
database credentials" (2026-10-22,
<https://blog.railway.com/p/security-disclosure-recommendation-rotate-postgresql-database-credentials>).
The post recommends rotating the password of databases created from Railway's PostgreSQL
template if it may have been exposed. Our `Postgres` service was created from that
template, so the password was rotated as a precaution. There was no sign of a leak before
or after.

All times UTC. **Owner** = done by me in the Railway dashboard or a terminal; **Agent** =
run by Claude Code from the laptop. No secret value was printed or saved: variables were
compared by the first 10 characters of their SHA-256 hash.

## Summary

| | |
|---|---|
| Password regenerated | 2026-10-24, about 20:10 (Owner, dashboard) |
| Database restarted | 20:10:36 (`pg_postmaster_start_time()`) |
| App reconnected | Deployment `2c3a871c`, created 20:10:29, `SUCCESS` about 20:12:30 |
| Visitors during the gap | 20:10:44 to 20:12:38: HTTP **503** with the profile and "Projects temporarily unavailable"; one request got no answer during the deployment switch |
| Old password | Rejected: 46 `password authentication failed` log lines from the old deployment during the gap |
| Signs of misuse | None found (sessions, roles, extensions, row counts, latest edits) |
| Public database access | Already off before the rotation (no TCP proxy) |

## 1. Before rotating (guide: find consumers, check public access)

**Consumers of the database credentials** (Agent, 20:09:04, `railway variables --json`
for both services, hashed):

| Variable | Fingerprint | Host |
|---|---|---|
| `career-platform` → `DATABASE_URL` | `6c4142c8f0`, password `7e9e5c206b` | private `*.railway.internal:5432`, database `railway` |
| `Postgres` → `DATABASE_URL` | `6c4142c8f0`, password `7e9e5c206b` | same |
| `Postgres` → `POSTGRES_PASSWORD` | `7e9e5c206b` | |
| `Postgres` → `DATABASE_PUBLIC_URL` | absent | |

The app is the only service using the database. Its `DATABASE_URL` was set on
2026-10-10 as the reference `${{Postgres.DATABASE_URL}}` (Railway plan, R2). The CLI shows
only resolved values; the rotation confirmed the reference (section 3).

**Public access:** the `Postgres` service had no `DATABASE_PUBLIC_URL` and no
`RAILWAY_TCP_PROXY_*` variables, so its TCP proxy was already removed. Nothing to turn
off.

**Copies of the credential outside Railway** (Agent):

| Where | Found | Action |
|---|---|---|
| Git history, all branches (`git log --all -p`) | No real credential. Every Postgres URL is a test fixture (`u:p@…`, the percent-encoding test value) or the local Docker database | None |
| `.superpowers/` work notes (Git-ignored) | Railway-style URLs, all with the test password `p` | None |
| Local `.env` (Git-ignored, never committed) | `RAILWAY_DATABASE_URL`: a public-proxy connection string with a real password, from the migration on 2026-10-10 | Line deleted after the rotation (section 5) |
| Shell histories, `~/Downloads/railway-migration` | None | None |

## 2. Regenerate the password (guide steps 4–6)

Owner, about 20:10: Railway → `Postgres` → **Database** → **Config** → **Regenerate**.

A background check fetched `https://caelonk.me/` every 3 seconds from 20:09:36 (141
requests):

| Time | Result |
|---|---|
| 20:09:36 to 20:10:34 | `200`, 5 projects |
| 20:10:44 | First `503`, in 6.1 s (the app's 3 s connect timeout, tried on both of the database's addresses) |
| 20:10:47 to 20:12:19 | `503`, 27 in total, each 0.1 to 0.4 s after the first; every one showed my profile and "Projects temporarily unavailable" |
| 20:12:23 | No answer within 15 s, during the switch to the new deployment |
| 20:12:42 onward | `200`, 5 projects |

The page never hung and never showed old content. This is the behavior from
[`database-outage-check.md`](database-outage-check.md), now seen on the live site.

## 3. Redeploy the app (guide steps 7–10)

Railway started a redeploy of `career-platform` itself at 20:10:29 (deployment
`2c3a871c-0b46-47c0-bfa2-173d25afca3a`, reason `redeploy`, commit `f7de140`). The Agent's
`railway redeploy --service career-platform` at 20:11:35 was refused because that
deployment was already building. It went `BUILDING` → `DEPLOYING` → `SUCCESS` by about
20:12:30.

**Fingerprints after** (Agent, 20:11:21):

| Variable | Before | After |
|---|---|---|
| `career-platform` → `DATABASE_URL` | `6c4142c8f0` | `e7fc6e3ce6` |
| `Postgres` → `DATABASE_URL` | `6c4142c8f0` | `e7fc6e3ce6` |
| Password in both, and `POSTGRES_PASSWORD` | `7e9e5c206b` | `681bac4c13` |

The app's value changed with the database's without anyone editing it, so it is a
reference, as the guide requires. No pasted connection strings needed replacing. No
external consumers existed (step 10).

## 4. Verify (guide steps 11–15) and look for misuse (16–19)

**Logs:**

| Deployment | Result |
|---|---|
| Old, `c69f1f48` | 46 lines of `FATAL: password authentication failed for user "postgres"`, each turned into a 503 with `Database read failed for the home page`. The old password stopped working |
| New, `2c3a871c` | Pre-deploy `alembic upgrade head` connected (`Context impl PostgresqlImpl.`); `[1/1] Healthcheck succeeded!`; in 120 log lines: 0 authentication failures, 0 `Database read failed`, 0 tracebacks, 0 5xx responses, 106 `200` responses |

**Database checks** (Agent, 20:17:20, inside the `Postgres` container over
`railway ssh`, with `psql` in a read-only session, `default_transaction_read_only=on`):

| Check | Result |
|---|---|
| Server | PostgreSQL 18.6, started 20:10:36 (the rotation restart) |
| Sessions (`pg_stat_activity`) | Two idle sessions from the app over the private network, started 20:12:40 and 20:12:44 (the new deployment), plus the check itself. None unrecognized, so none terminated |
| Roles that can log in | `postgres` only; the rest are PostgreSQL's built-in `pg_*` roles |
| Extensions | `plpgsql` only |
| Tables | The 13 app tables and `alembic_version`, nothing else |
| Row counts | Same as the 2026-10-10 migration (profiles 1, project_metrics 6, organizations 3, roles 5, skills 39, project_skills 7, experiences 5, experience_skills 9, certifications 2, others 0), except projects 6: the 4 migrated, `sequence-check` (V3, 2026-10-15) and "This website is in progress" (2026-10-21) |
| Latest edits | Profile and experiences 2026-09-29; projects 2026-10-21 05:06 (my own edit). Nothing changed after that |
| Migration | `20240917_initial_schema` |

**Not checked:** Railway's audit logs (the guide links them under its Enterprise docs;
not used here). PostgreSQL doesn't log successful connections by default, so connections
before the rotation can't be reviewed. No backup restore was needed.

**Setup for the database checks** (Owner): `railway ssh keys add` registered the public
key `isba4775_azure` with Railway, and the first `railway ssh --service Postgres -- echo ok`
accepted Railway's SSH host key.

## 5. Clean-up and site check after the rotation

- Deleted `RAILWAY_DATABASE_URL` from the local `.env` (Agent). The file is Git-ignored
  and the app never read that variable; local development still uses SQLite.
- Live checks, 20:18 UTC: `/`, `/health`, `/privacy`, `/resume.pdf` and the four project
  pages `200`; an unknown project `404`; `http://caelonk.me/`, `http://www.caelonk.me/`
  and `https://www.caelonk.me/` all `301` to `https://caelonk.me/`; no outage message;
  certificate valid to 2027-01-06.

## What this showed

- `/health` doesn't touch the database, so Railway's health check passed even while the
  app couldn't log in. The guide warns about exactly this. The home page's 503 is what
  showed the problem, and is the better thing to watch after a credential change.
- Because the app reads `${{Postgres.DATABASE_URL}}`, the new password reached it
  without anyone copying it.
- The plain-text copy in `.env` was the one place the credential lived outside Railway.
  It is gone, and it was already useless (old password, removed proxy).
- Railway now warns that `railway.json` (config as code) is deprecated and keeps working
  until 2026-12-01. The pre-deploy command and health check are set on the service, so
  this doesn't change how the site deploys.
