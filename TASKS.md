# Project 1 gaps

From the requirements audit on 2026-10-20. Each line names the file or check that closes it.

## Cross-cutting

- [ ] Create the submission index → `docs/project-1-submission.md`
- [ ] Rewrite the stale README (Status, Next milestones, sections for requirement 8) → `README.md`
- [ ] Ask the instructor about the VM being deallocated since 2026-10-13, or start it again → Azure portal, `az vm show -d … --query powerState`
- [ ] Merge `docs/ex06-results-sheet` (`bb57977`) into `main` → `git log main..docs/ex06-results-sheet` is empty

## 1. Profile and project data

- [ ] On a database failure, keep the profile, show "Projects temporarily unavailable" and return 503 instead of serving the snapshot with 200 → `app/routes/public.py`, `app/templates/public/home.html`
- [ ] Replace the test that expects 200 with tests for 503, the message and the visible profile → `tests/routes/test_snapshot_fallback.py`
- [ ] Test that a refresh after the database recovers shows projects again, without a restart → new test in `tests/routes/`
- [ ] Add an education section → `app/templates/public/home.html` (and the model, if stored in the database)
- [ ] Add professional links (LinkedIn, GitHub) → `app/templates/public/home.html` or profile data
- [ ] Add a project entry describing this website, labeled in progress → admin "Create project" on `https://caelonk.me`
- [ ] Explain why SQLite was the first database engine → README decisions section

## 2. Azure deployment

- [ ] Make the systemd unit match what ran on the VM (`azureuser`, home paths, `--workers 2`) → `deploy/systemd/career-platform.service`
- [ ] Save the Nginx config that served 443 on the VM → `deploy/nginx/career-platform.conf`
- [ ] Fix the runbook that says Azure Database for PostgreSQL → `deploy/azure/README.md`
- [ ] Mark the provisioning plan as not executed → `docs/superpowers/plans/2026-09-29-azure-vm-provisioning.md`

## 3. Domain and HTTPS

- [ ] Record the Railway certificate (hostname, validity, how Railway renews it) → `openssl s_client -connect caelonk.me:443 -servername caelonk.me | openssl x509 -noout -subject -issuer -dates`, saved in the README or `docs/evidence/`
- [ ] Run the planned Domain 3 check and record dated results → Railway plan, Domain section

## 4. Railway and PostgreSQL migration

- [ ] Record a real change to the original project data, or mark it as not done → Railway plan, Data section
- [ ] Compare the rendered page on the source and the target → Railway plan or `docs/evidence/`
- [ ] Add a "what Git moves versus what needs another method" list → Railway plan or README
- [ ] Add a table of who manages what on Azure versus Railway, plus what you're still responsible for → README
- [ ] Link the spec and the migration plan → `README.md`, `docs/project-1-submission.md`

## 5. Reviewed change through Railway

- [ ] Tie one commit to its Railway deployment ID and what was seen at `caelonk.me` → `railway deployment list --service career-platform`, recorded in `docs/evidence/`
- [ ] Record the diff review and the local check before pushing → same evidence file
- [ ] Write the rollback section for code and database changes → `README.md`

## 6. Zoho email

- [ ] Add the before-MX line, explaining that Namecheap's mail records existed from 2026-10-06 → `docs/evidence/ex06.md`
- [ ] Create the header analysis → `docs/evidence/zoho-header-check.md`
- [ ] Compare the DKIM key and verification code with the Zoho console → `docs/evidence/dns-after-zoho.md`
- [ ] Link both evidence files → `README.md`, `docs/project-1-submission.md`

## 7. GA4

- [ ] Explain how a browser event reaches GA4 (gtag, request to Google, Realtime) → `docs/evidence/ex06.md` or README
- [ ] Explain why an outbound click is useful for this site → same file

## 8. Engineering record

- [ ] Add Azure and Railway diagrams with the email and analytics paths → README or `docs/`
- [ ] Write at least two decisions with alternatives (Railway, managed versus self-hosted email) → `README.md`
- [ ] Link the failure write-ups `docs/evidence/ex03.md` and `docs/evidence/ex05.md` (simulation), and list remaining limits → `README.md`
- [ ] Write a short reflection → `README.md`
- [ ] Record costs, the Railway trial end date, renewals and cleanup plans → `README.md`
- [ ] Confirm which file is your own Ex04 HTTPS explanation → `docs/how-this-site-is-secured.md` or the correct file
