# Career Platform

My personal career site at **<https://caelonk.me>**: profile, education, contact details,
a downloadable resume, and project case studies read from a database on every request.
It began in Codespaces, ran on an Azure Linux VM, and now runs on Railway with
PostgreSQL. It is the starting point for the career platform built through the semester.

- Project 1 submission index: [`docs/project-1-submission.md`](docs/project-1-submission.md)
- Original spec: [`docs/superpowers/specs/2026-09-15-personal-career-platform-design.md`](docs/superpowers/specs/2026-09-15-personal-career-platform-design.md)
- Plans: [`docs/superpowers/plans/`](docs/superpowers/plans/)

## What it does

| Page | What it shows | Where the content comes from |
|---|---|---|
| `/` | Name, headline, introduction, projects, education, contact, LinkedIn and GitHub links | Profile and published projects from the database; education and links from `app/site_content.py` |
| `/projects/<slug>` | One case study: context, problem, approach, outcomes, metrics | Database (published projects only) |
| `/resume.pdf` | Resume | `app/static/resume/resume.pdf` |
| `/privacy` | What Google Analytics collects and how to opt out | Template |
| `/admin` | Log in, create and edit projects | Database; password hash in `ADMIN_PASSWORD` |
| `/health` | `{"status":"ok"}` for Railway's health check | Code only (doesn't touch the database) |

**When the database is down,** the home page keeps the last profile it read, says
"Projects temporarily unavailable." and returns **HTTP 503**. Project pages return 503.
The next request after the database recovers reads it again, with no restart. A healthy
request returns 200. Evidence: [`docs/evidence/database-outage-check.md`](docs/evidence/database-outage-check.md).
An empty projects table shows "No projects are published right now."

## How it runs now (Railway)

```mermaid
flowchart LR
  B["Visitor's browser"]
  subgraph CF["Cloudflare (DNS host for caelonk.me)"]
    DNS[("Authoritative DNS<br/>@ CNAME → l29it1kr.up.railway.app (DNS only)<br/>www A placeholder (proxied)<br/>MX, SPF, DKIM, DMARC → Zoho")]
    EDGE["Cloudflare edge<br/>www → 301 https://caelonk.me"]
  end
  subgraph RW["Railway: project motivated-solace, environment production"]
    REDGE["Railway edge<br/>TLS ends here<br/>Let's Encrypt cert for caelonk.me"]
    APP["career-platform service<br/>Docker image, Uvicorn, 2 workers<br/>on $PORT (8080)"]
    PG[("Postgres service<br/>PostgreSQL 18<br/>private network, TCP 5432")]
    VOL[("Volume /data<br/>snapshots, profile.json")]
  end
  GH["GitHub<br/>caelonk/career-platform, main"]
  GA["Google Analytics 4<br/>G-6J1F90ST16"]
  GTM["www.googletagmanager.com<br/>gtag.js"]

  B -- "1. DNS lookup, UDP 53" --> DNS
  B -- "2. HTTPS, TCP 443 (HTTP 80 → 301)" --> REDGE
  B -. "www.caelonk.me, TCP 80/443" .-> EDGE
  REDGE -- "3. plain HTTP + X-Forwarded-Proto" --> APP
  APP -- "4. SQL, psycopg" --> PG
  APP --- VOL
  GH -- "push to main → build + alembic upgrade head → /health gate" --> APP
  B -- "5. HTTPS 443, load gtag.js" --> GTM
  B -- "6. HTTPS 443, page_view and click events" --> GA
```

**Email** (Zoho Mail, `caelon@caelonk.me`) doesn't touch Railway:

```mermaid
flowchart LR
  EXT["Outside sender<br/>(e.g. Gmail)"]
  DNS[("Cloudflare DNS<br/>MX mx/mx2/mx3.zoho.com<br/>SPF include:zohomail.com<br/>DKIM zmail._domainkey<br/>DMARC p=none")]
  ZMX["Zoho inbound servers<br/>SMTP, TCP 25"]
  ZBOX[("Zoho mailbox<br/>caelon@caelonk.me")]
  ME["Me, in Zoho webmail<br/>HTTPS 443"]
  ZOUT["Zoho outbound servers<br/>sign with DKIM"]
  RCPT["Recipient's mail server<br/>checks SPF, DKIM, DMARC in DNS"]

  EXT -- "1. look up MX" --> DNS
  EXT -- "2. SMTP 25" --> ZMX --> ZBOX
  ME <--> ZBOX
  ME -- "3. send or reply" --> ZOUT
  ZOUT -- "4. SMTP 25" --> RCPT
  RCPT -. "5. TXT lookups" .-> DNS
```

**Analytics** goes from the visitor's browser straight to Google; the app only sends the
HTML containing the tag. Details and the Realtime check: [`docs/evidence/ex06.md`](docs/evidence/ex06.md) section 4.

A step-by-step request trace (DNS, TCP, TLS, HTTP) is in
[`docs/midterm-request-path.md`](docs/midterm-request-path.md).

## How it ran before (Azure VM)

```mermaid
flowchart LR
  B["Visitor's browser"]
  L["My laptop"]
  DNS[("Cloudflare DNS<br/>A @ and www → 52.162.50.66, DNS only")]
  LE["Let's Encrypt"]
  subgraph AZ["Azure, northcentralus, rg-career-platform"]
    PIP["Public IP 52.162.50.66<br/>(held by Azure, 1:1 NAT)"]
    NSG{{"NSG vm-career-platformNSG<br/>22 from my laptop /32 only<br/>80, 443 from anyone<br/>everything else denied"}}
    subgraph VM["Ubuntu 24.04 VM, private IP 10.0.0.4"]
      NGX["Nginx :80 → 301<br/>Nginx :443, TLS ends here"]
      UV["Uvicorn 127.0.0.1:8000<br/>2 workers, systemd, as azureuser"]
      DB[("SQLite file<br/>~/career-platform/career_platform.db")]
      CB["certbot.timer"]
    end
  end
  B -- "DNS, UDP 53" --> DNS
  B -- "TCP 80/443" --> PIP --> NSG --> NGX
  NGX -- "HTTP over loopback" --> UV --> DB
  L -- "SSH, TCP 22, key only" --> PIP
  CB -- "renew, HTTP-01 on port 80" --> LE
```

While the VM served the site there was **no GA4** (added 2026-10-15) and **no Zoho**
(set up 2026-10-13). The domain's MX records pointed at Namecheap forwarding, which
rejected incoming mail, so the email path above didn't exist yet. Details:
[`deploy/azure/README.md`](deploy/azure/README.md),
[`docs/how-this-site-is-secured.md`](docs/how-this-site-is-secured.md).
The VM is running again since 2026-10-21 as the rollback copy; no DNS record points at it.

## Set up and run locally

```bash
python -m venv .venv && . .venv/Scripts/activate   # or bin/activate
python -m pip install -e '.[dev]'
cp .env.example .env                               # local SQLite by default
alembic upgrade head
python -m pytest -q
uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8000 --reload
```

The local database starts empty; add content through `/admin`. `ADMIN_PASSWORD` holds a
pbkdf2 hash (make one with `app.services.auth.hash_password`). It is optional in
development, and production refuses the repository's default hash and default
`SECRET_KEY`.

Postgres-only tests need a local database and wipe its `public` schema, so they refuse
any address that isn't on this machine:

```bash
docker compose --profile postgres up -d postgres
TEST_POSTGRES_URL=postgresql://career_platform:career_platform@localhost:5432/career_platform python -m pytest -q
```

## Production settings (Railway)

| Setting | Where it lives |
|---|---|
| `DATABASE_URL` | Railway variable, a reference to `${{Postgres.DATABASE_URL}}` |
| `SECRET_KEY`, `ADMIN_PASSWORD` | Railway variables, never in Git |
| `ENVIRONMENT=production`, `SNAPSHOT_DIR=/data/snapshots` | Railway variables |
| Pre-deploy `alembic upgrade head`, health check `/health` | Railway service settings (Railway ignores `railway.json` for this service) |
| Custom domain `caelonk.me` | Railway service networking, plus Cloudflare DNS |

## Updating the site

1. Work on a branch. Run `python -m pytest -q` and check the change locally.
2. Open a pull request and review the diff.
3. Merge to `main`. Railway builds the `Dockerfile`, runs `alembic upgrade head`, waits
   for `/health` to return 200, then switches traffic. A failed build or health check
   leaves the previous deployment serving.
4. Check `railway deployment list --service career-platform` for the new deployment and
   its commit SHA, then check the change at `https://caelonk.me`.

Example with evidence: [`docs/evidence/reviewed-change.md`](docs/evidence/reviewed-change.md).
Later changes followed the same path: admin slug validation (PR #8) and the Featured
checkbox (PR #9), both deployed on 2026-10-24.

## Rollback

### Bad code

- **Fastest:** Railway dashboard → `career-platform` → Deployments → the last good
  deployment → **Redeploy**. That reruns the old image with the settings it had then.
- **Lasting:** `git revert <bad sha>` on a branch, review, merge to `main`. Railway
  builds the reverted code. Prefer this, so `main` matches what is live.
- Check: `railway deployment list` shows the deployment `SUCCESS`, and the problem is gone
  at `https://caelonk.me`.

### Bad data or a bad migration

- **Before** a change that edits or deletes data, or a new migration, take a dump. The
  laptop has no `pg_dump`, so run it from the Postgres image with the public URL injected
  by Railway:
  `railway run --service Postgres -- docker run --rm -e DATABASE_PUBLIC_URL postgres:18 sh -c 'pg_dump --no-owner "$DATABASE_PUBLIC_URL"' > backup-YYYYMMDD.sql`
  (keep the file outside the repository; it contains personal data). *Not yet rehearsed.*
- **A wrong admin edit:** fix it again in `/admin`; every change is a normal row update.
- **A bad migration:** write a new migration that reverses it, or restore the dump into
  an empty database. The current single migration has no earlier state to go back to.

### Back to the Azure VM

The full procedure is in the Railway plan's
[Rollback section](docs/superpowers/plans/2026-10-08-railway-postgres-migration.md#rollback-any-point-after-domain-2).
In short: point `@` and `www` back at `52.162.50.66` (DNS only), remove the `www`
redirect rule, and confirm the VM serves. The VM's SQLite file is frozen at 2026-10-08,
so **data written on Railway since 2026-10-10 must be moved first**: dump it as above,
then re-enter or copy the changed rows into the VM's database before switching DNS. The
VM's certificate expires 2027-01-04 and will only renew once DNS points back at it.

## Migration from Azure to Railway

- **Plan, written before the change:** [`docs/superpowers/plans/2026-10-08-railway-postgres-migration.md`](docs/superpowers/plans/2026-10-08-railway-postgres-migration.md)
  (committed 2026-10-08 21:40 UTC as `ae8b4f5`; the domain was first attached to Railway at 22:16 UTC).
- **Compatibility changes:** Postgres driver and URL handling (`dba4993`), migrations from
  code and Postgres tests (`aa519d9`), copy script with id-sequence reset (`3dccd86`),
  Railway container (`df4ef2a`), production secret checks (`d41968c`, `776b3fa`).
- **Data:** the VM's SQLite file was backed up, copied to the laptop (same SHA-256), and
  copied into Railway Postgres; every row of all 13 tables matched (plan, D2–D3). On
  2026-10-21 the five public pages from the VM and from Railway had identical text
  ([`docs/evidence/azure-vm-check-2026-10-21.md`](docs/evidence/azure-vm-check-2026-10-21.md)).
  **Gap:** no deliberate change was made to the data before the copy, as the course asks.
- **Cutover and checks:** plan sections R4, V1–V3, Domain and S1; today's re-check in
  [`docs/evidence/live-checks-2026-10-21.md`](docs/evidence/live-checks-2026-10-21.md).
- What Git moved and what it didn't: the plan's "Added afterward" section.

### Who manages what

| Part | Azure VM (IaaS) | Railway (PaaS) | Still mine on Railway |
|---|---|---|---|
| Operating system, patches | Me (Ubuntu updates) | Railway | Nothing |
| Runtime (Python, packages) | Me (venv on the VM) | Built by Railway from my `Dockerfile` and `uv.lock` | Choosing versions and updating the lock file |
| Process management | Me (systemd unit, workers) | Railway (restart policy, health check) | The start command and worker count in the `Dockerfile` |
| Web entry point | Me (Nginx, NSG rules) | Railway edge | Nothing to configure, but no control over it either |
| TLS certificate | Me (Certbot, timer) | Railway | Keeping the apex DNS record pointed at Railway so renewal works |
| Application code | Me | Me | All of it, plus reviewing what reaches `main` |
| Configuration and secrets | Me (`.env` on the VM) | Me (Railway variables) | Strong values, rotation, never committing them |
| Database software | Me (SQLite file) | Railway (Postgres service) | Major-version upgrades are still my decision |
| Data and backups | Me | Me | Dumps before risky changes; whether Railway backups are on hasn't been checked |
| DNS | Me (Cloudflare) | Me (Cloudflare) | Unchanged |
| Cost | Me (Azure budget) | Me (Railway trial) | Watching the trial end date and usage |

## Decisions

> Drafted by Claude Code on 2026-10-20, after the work, from the records linked here.

1. **Railway for the second host.** I could have stayed on the Azure VM, which I already
   had working with HTTPS, restarts and service management. I moved to Railway because a
   PaaS takes over the operating system, patching, Nginx and the certificate, which were
   the parts that took the most of my time on the VM. The trade-offs showed up quickly:
   Railway ignored my `railway.json`, so I had to set the pre-deploy command and health
   check on the service; the trial allows one custom domain, so `www` became a
   Cloudflare redirect instead of a second Railway domain; and the trial ends, so the
   site has to move again.
2. **Managed email with Zoho instead of running my own mail server.** The alternatives
   were Postfix and Dovecot on the VM, or keeping Namecheap's forwarding. Running mail
   myself would mean a sending IP with no reputation, outbound port 25 that cloud
   providers often block, and spam filtering, DKIM signing, storage and backups all on me.
   Namecheap forwarding wasn't an option either: its server answered
   `554 Relay access denied` for my address. Zoho's free plan gives me one real mailbox
   on my domain, and I publish the DNS records it needs in Cloudflare.
3. **SQLite first, PostgreSQL on Railway.** The VM had 1 GiB of RAM, and the only writer
   is me through `/admin`, so a single SQLite file was enough, and the course kept the
   engine the same for the first move. I wrote the app against SQLAlchemy and Alembic
   from the start, because the spec named PostgreSQL as the target. That made the later
   switch a driver and URL change plus a data copy, not a rewrite.
4. **Show the outage instead of hiding it.** My original spec served a saved snapshot
   when the database failed, which returned 200 and looked healthy. I changed it so the
   page keeps my profile, says projects are temporarily unavailable, and returns 503, so
   a monitor or a visitor can tell something is wrong, and old content never passes as
   current.

## Failures investigated

| Failure | Type | Record |
|---|---|---|
| Azure region and VM size blocked, auto-shutdown failures, an empty database to migrate | Build / Azure migration | [`docs/evidence/ex03.md`](docs/evidence/ex03.md) "What broke" |
| Stale A record sends `site.lab.example` to the old VM, so TLS fails on name mismatch | DNS / TLS, **lab simulation supplied with Exercise 5, not my domain** | [`docs/evidence/ex05.md`](docs/evidence/ex05.md) |
| Requests hang when the database stops, instead of returning 503 | Application / database dependency, found 2026-10-21 | [`docs/evidence/database-outage-check.md`](docs/evidence/database-outage-check.md) |
| Incoming mail bounced while Namecheap and Zoho MX records were both published | DNS / email | [`docs/evidence/zoho-header-check.md`](docs/evidence/zoho-header-check.md) section 2 |
| `https://www.caelonk.me` timed out after the `www` record lost its proxy | DNS | Railway plan, Mail section, "Incident during the setup" |
| Railway ignored `railway.json`: no pre-deploy migration, no health check | Deployment | Railway plan, R4 results |
| Database password rotated after Railway's 2026-10-22 security disclosure; site served 503 for about 2 minutes, old password rejected, no signs of misuse | Security / database dependency, 2026-10-24 | [`docs/evidence/railway-credential-rotation-2026-10-24.md`](docs/evidence/railway-credential-rotation-2026-10-24.md) |
| Admin accepted blank or spaced slugs (`/projects/%20`) and featured every published save | Application, fixed 2026-10-24 | PR #8, PR #9 |
| `502 Bad Gateway` for a few seconds after a VM boot | Application startup | Operate-the-VM plan, Restart 1 finding |

## Limitations

- No deliberate data change was made before the Railway copy (see Migration).
- The 503 behavior was tested against a local Postgres, not by stopping Railway's
  database.
- Railway Postgres backup settings haven't been checked, and the dump procedure above
  hasn't been rehearsed.
- The `/data/snapshots` volume contents were never listed.
- `/health` doesn't query the database, so Railway's health check stays green when the
  app can't reach it (seen during the credential rotation). The home page's 503 shows it.
- Railway says `railway.json` stops being read on 2026-12-01; the deploy settings live on
  the service, and the site moves to AWS before then.
- `HEAD /` returns 405, because routes accept only `GET`.
- DMARC is `p=none`; aggregate reports aren't read yet.
- The experience section of my resume isn't on the site yet.
- The "This website is in progress" project has a placeholder slug (`-`) and an empty
  summary; admin doesn't yet reject blank titles or summaries.

## Reflection

> Drafted then edited with Claude Code on 2026-10-20, after the work, from the records linked here.

**What I understand better.** An error often shows up one layer away from its cause.
In Exercise 5, curl reported a certificate error, but the cause was a stale DNS record
sending me to the wrong server. On the VM, a `502` right after a reboot wasn't a broken
setup, just Nginx starting a few seconds before Uvicorn. And when I tested the database
outage, the page didn't return the 503 I'd written; it hung, because the connection had
no timeout. In each case the fix was where the evidence pointed, not where the symptom
appeared. I also understand now that PaaS moves work rather than removing it: on Railway
I still own the code, secrets, data, backups, DNS and the bill.

**What I would change.** I would write the deliberate data change into the migration
plan before copying, so the comparison could prove it carried current data. I would keep
the deploy files in the repository identical to the server from the first day; mine
drifted until I copied the real Nginx file back. I would check where the domain actually
pointed before planning the cutover: `caelonk.me` was already aimed at Railway for two
days before Railway had a working deployment. And I would watch the Railway trial clock
and turn on database backups from the start.

## Costs, expiry and cleanup

| Service | What is billed or limited | Cost / credit | Ends or renews | Cleanup plan |
|---|---|---|---|---|
| Azure for Students | VM compute while running; OS disk and static public IP even when stopped | Budget `budget-isba4775`: **$3.99 of $15** spent in the current period (read 2026-10-21). Auto-shutdown is off, so compute bills while the VM runs | The portal shows current cost only ($3.99 from use, 2026-10-21), no credit expiry date | Keep running until the instructor's cleanup directions; then delete `rg-career-platform` (VM, disk, IP, NSG) |
| Railway | Trial: 30 days or $5 of usage, whichever comes first; app service, Postgres service and volume | **$4.11 of $5 left** (dashboard, 2026-10-20) | **16 days left on 2026-10-20, so the trial ends about 2026-11-05** | Migrate to AWS after the midterm and before 2026-11-05; then delete the Railway project |
| Cloudflare | DNS for `caelonk.me` | Free plan | No expiry | Keep |
| Namecheap | Domain `caelonk.me`, registered 2026-10-05 | Not recorded | **Expires 2027-10-05** (Namecheap dashboard) | Renew before 2027-10-05, or let it lapse if the site moves to another name |
| Zoho Mail | One mailbox, `caelon@caelonk.me` | Forever Free plan | No expiry | Keep |
| Google Analytics 4 | Property for `caelonk.me` | Free | No expiry | Keep |

## Repository map

```text
app/                FastAPI app: routes, services, templates, static files
app/site_content.py education and profile links (not in the database)
migrations/         Alembic migrations
scripts/            copy_sqlite_to_postgres.py (used for the Railway move)
tests/              pytest suite (routes, database, operations, end-to-end)
deploy/             Azure VM files: systemd unit, Nginx site, runbook
Dockerfile          Railway build
docs/superpowers/   original spec and plans, with dated results
docs/evidence/      exercise evidence and dated checks
```
