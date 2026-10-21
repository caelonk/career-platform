# A reviewed change, from commit to the live site

The change: the home page returns **503** with the profile kept and "Projects temporarily
unavailable." when the database fails, instead of an old snapshot with 200.

## 1. The change

| | |
|---|---|
| Commit | `3c2117b` "fix: return 503 with the profile kept when the database is down" |
| Files | `app/routes/public.py`, `app/services/profile_fallback.py` (new), `app/db/session.py` (3 s connect timeout), `app/templates/public/home.html`, tests |
| Branch and pull request | `project-1-gaps`, [PR #3](https://github.com/caelonk/career-platform/pull/3) |

## 2. Review and local checks, before merging

| Check | Result |
|---|---|
| Tests written first and watched failing | 7 of 8 new outage tests failed before the change (the healthy-page test already passed), and the connect-timeout test failed with `KeyError: 'connect_args'` |
| Full suite after the change | `67 passed, 3 skipped` (now 70 with the education tests) |
| Real Postgres stopped and started, app running with 2 workers | 200 → 503 with the profile and message → 200 after restart, with no app restart. [`database-outage-check.md`](database-outage-check.md) |
| Problem found by that check | Requests hung when the database stopped; fixed with the connect timeout before merging (same file) |
| Review | The diff and the check results above were summarized in PR #3; the Owner approved the merge on 2026-10-21. No line comments were left |

## 3. Deployment and live check

| Check | Result |
|---|---|
| Merge commit on `main` | `714a6f1` "Merge pull request #3 from caelonk/project-1-gaps", merged 2026-10-21 04:48:16 UTC |
| Railway deployment | `dfd152cb-bd5f-4d54-89f2-a0668b1d7e79`, commit `714a6f1`, created 04:48:18 UTC (2 s after the merge), `BUILDING` → `DEPLOYING` → **`SUCCESS`** by 04:49:01 (`railway deployment list --service career-platform --json`) |
| Pre-deploy migration | Deploy log: `Context impl PostgresqlImpl.`, no `Running upgrade` line, because this change has no migration |
| Health check gate | Build log: `Starting Healthcheck`, `[1/1] Healthcheck succeeded!` |
| Startup | `Uvicorn running on http://0.0.0.0:8080`, two server processes, `Application startup complete` |
| `https://caelonk.me/` at 04:49:14 UTC | `HTTP/1.1 200 OK`, `Server: railway-hikari`; my name 5 times, "Technician Dispatch Dashboard" present, "Projects temporarily unavailable" absent |
| A change visible only in the new code | The Education section (`id="education-title"`, "Loyola Marymount University") and the `https://github.com/caelonk` link, both from `5a9cc77` in the same merge |
| Other pages | `/health` 200, `/projects/technician-dispatch-dashboard` 200, `/projects/legal-document-analyzer` 200 |

The 503 path itself wasn't triggered on the live site, because that means stopping
Railway's database. It is covered by the local check and the tests above.

## 4. If it had gone wrong

Redeploy the previous Railway deployment from the dashboard, then `git revert` the merge
on a branch and merge that. This change has no database migration, so no data step is
needed. The README's [Rollback](../../README.md#rollback) section covers both code and data.
