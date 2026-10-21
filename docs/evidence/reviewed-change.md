# A reviewed change, from commit to the live site

The change: the home page returns **503** with the profile kept and "Projects temporarily
unavailable." when the database fails, instead of an old snapshot with 200.

## 1. The change

| | |
|---|---|
| Commit | `3c2117b` "fix: return 503 with the profile kept when the database is down" |
| Files | `app/routes/public.py`, `app/services/profile_fallback.py` (new), `app/db/session.py` (3 s connect timeout), `app/templates/public/home.html`, tests |
| Branch and pull request | `project-1-gaps`; *pull request number: filled in when opened* |

## 2. Review and local checks, before merging

| Check | Result |
|---|---|
| Tests written first and watched failing | 7 of 8 new outage tests failed before the change (the healthy-page test already passed), and the connect-timeout test failed with `KeyError: 'connect_args'` |
| Full suite after the change | `67 passed, 3 skipped` (now 70 with the education tests) |
| Real Postgres stopped and started, app running with 2 workers | 200 → 503 with the profile and message → 200 after restart, with no app restart. [`database-outage-check.md`](database-outage-check.md) |
| Problem found by that check | Requests hung when the database stopped; fixed with the connect timeout before merging (same file) |
| Diff review by the Owner | *Pending: approved on (date) in the pull request* |

## 3. Deployment and live check

*Pending: filled in after the merge to `main`.*

| Check | Result |
|---|---|
| Merge commit on `main` | |
| Railway deployment ID, status, commit SHA | |
| Pre-deploy migration and `/health` gate in the deploy log | |
| `https://caelonk.me/` after the deploy | |
| A change visible only in the new code | |

## 4. If it had gone wrong

Redeploy the previous Railway deployment from the dashboard, then `git revert` the merge
on a branch and merge that. This change has no database migration, so no data step is
needed. The README's [Rollback](../../README.md#rollback) section covers both code and data.
