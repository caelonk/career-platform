# Project 1 gaps

From the requirements audit on 2026-10-20. Each line names the file or check that closes it.
Updated 2026-10-21 on branch `project-1-followup`.

## Cross-cutting

- [x] Create the submission index → `docs/project-1-submission.md`
- [x] Rewrite the stale README (Status, Next milestones, sections for requirement 8) → `README.md`
- [x] Start the VM again (it was deallocated since 2026-10-13) → `docs/evidence/azure-vm-check-2026-10-21.md`
- [x] Merge PR #1 and PR #3 into `main` → merged 2026-10-21 as `714a6f1`
- [ ] Fill in the final commit SHA at submission → `docs/project-1-submission.md`

## 1. Profile and project data

- [x] Return 503 with the profile kept and "Projects temporarily unavailable" on a database failure → `app/routes/public.py`, `app/services/profile_fallback.py`
- [x] Replace the test that expected 200 → `tests/routes/test_database_outage.py`
- [x] Test that a refresh after recovery shows projects again → same file, and `docs/evidence/database-outage-check.md` (real Postgres)
- [x] Add an education section → `app/site_content.py`, `app/templates/public/home.html`
- [x] Add a GitHub link → `app/site_content.py`
- [x] Add a LinkedIn link → `app/site_content.py`
- [ ] Publish the "this website" project (created in `/admin` as a **draft**, so it isn't public yet) → set its status to Published, then check it appears on `https://caelonk.me`
- [x] Explain why SQLite was the first database engine → README "Decisions" 3 (draft)

## 2. Azure deployment

- [x] Make the systemd unit match the VM → `deploy/systemd/career-platform.service`
- [x] Save the Nginx config that served 443 → `deploy/nginx/career-platform.conf` (copied from the VM 2026-10-21)
- [x] Fix the runbook → `deploy/azure/README.md`
- [x] Mark the provisioning plan as not executed → `docs/superpowers/plans/2026-09-29-azure-vm-provisioning.md`

## 3. Domain and HTTPS

- [x] Record the Railway certificate and the `www` checks → `docs/evidence/live-checks-2026-10-21.md`

## 4. Railway and PostgreSQL migration

- [ ] Deliberate change to the original data before the copy → **recorded as a gap** in the Railway plan's "Added afterward"; can't be redone without clearing Railway's database (Owner decision)
- [x] Compare the rendered page on the source and the target → `docs/evidence/azure-vm-check-2026-10-21.md`
- [x] What Git moves versus what needs another method → Railway plan, "Added afterward"
- [x] Who manages what on Azure versus Railway → README "Who manages what"
- [x] Link the spec and the migration plan → README, submission index

## 5. Reviewed change through Railway

- [x] Review and merge → PR #3, `docs/evidence/reviewed-change.md` section 2
- [x] Railway deployment `dfd152cb` and the live check → same file, section 3
- [x] Rollback for code and data → README "Rollback"

## 6. Zoho email

- [x] Before-MX line → `docs/evidence/ex06.md`
- [x] Header analysis → `docs/evidence/zoho-header-check.md`
- [x] Link both → README, submission index
- [x] Zoho console status → Verified (Owner, 2026-10-21), recorded in `docs/evidence/dns-after-zoho.md`

## 7. GA4

- [x] How a browser event reaches GA4, and why the outbound click matters → `docs/evidence/ex06.md` section 4

## 8. Engineering record

- [x] Diagrams with email and analytics paths → README
- [x] Failures table with links, limitations → README
- [x] Decisions and Reflection written → README (marked as drafted by Claude Code after the work)
- [x] Railway trial end date (about 2026-11-05) and credit ($4.11 left) → README "Costs, expiry and cleanup"
- [x] Azure cost ($3.99; the portal shows no expiry date) and domain expiry (2027-10-05) → same table
- [x] Ex04 HTTPS explanation confirmed → `docs/how-this-site-is-secured.md`
