# AWS EC2 + RDS Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Run a verified copy of caelonk.me on one EC2 instance with a private Single-AZ RDS PostgreSQL database, reachable at `https://aws.caelonk.me`, while Railway keeps serving `caelonk.me` until cutover.

**Architecture:** Nginx on an Ubuntu EC2 instance terminates HTTPS and proxies to Uvicorn on `127.0.0.1:8000`, run by systemd as a non-root user. The app reaches RDS over the default VPC's private network with TLS verified against the RDS CA bundle. RDS has no public address; its security group accepts 5432 only from the web server's security group. Data comes from the tested Railway backup, restored from the EC2 instance.

**Tech Stack:** FastAPI, Uvicorn, SQLAlchemy + psycopg 3, Alembic, uv 0.12.20, Python 3.12, Nginx, Certbot, PostgreSQL 18 (RDS + client), AWS CLI 2.39 (`--profile isba-4775`), Cloudflare `cf` CLI.

**Spec:** The class guide `C:\Users\caekn\Downloads\aws-migration.md` (Session 17, sections 5–8) plus the decisions in this conversation (EC2 + RDS chosen over EC2 + local PostgreSQL; backups as in README "Backup record").

## Status

| Step | State |
|---|---|
| Guide 1–4 (budget, decision, backup, IAM user, CLI) | Done 2026-11-01 (drawing skipped by owner) |
| G1 cost estimate, G2 deployment policy review | Not started |
| Tasks 1–8 | Not started |
| Cutover (Task 9) | Not planned for class; needs its own go |

## Global Constraints

- Region `us-east-1` only. Every AWS command passes `--profile isba-4775 --region us-east-1`. Never use root or AdministratorAccess.
- Instance: `t3.small`, On-Demand, `CpuCredits=standard`, IMDSv2 required (`HttpTokens=required`), one public IPv4, Ubuntu 24.04 LTS amd64 (Canonical owner `099720109477`; latest at planning `ami-0d6dd9e8265d48906`, re-resolve at launch).
- Instance disk: 20 GB gp3, encrypted, delete on termination.
- RDS: PostgreSQL 18 (latest 18.x offered), `db.t4g.micro`, Single-AZ, 20 GB gp3 encrypted, no storage autoscaling, not publicly accessible, automated backups 7 days, deletion protection on.
- No NAT gateway, load balancer, Secrets Manager, or extra paid services.
- Railway keeps running and `caelonk.me` DNS stays on Railway until Task 9. Mail records (Zoho MX, SPF, DKIM) are never touched.
- Work on branch `aws-migration`. Never push or merge to `main` during this plan (main auto-deploys Railway).
- Secrets (DB password, `SECRET_KEY`, `ADMIN_PASSWORD`) are never printed, pasted into chat, or committed. Backups stay outside the repo.
- Each AWS resource is created once, after the owner approves the task's settings table.
- `ADMIN_PASSWORD` is a `pbkdf2_sha256$...` hash full of `$`. Never `source` or `xargs` the env file in a shell. Run one-off commands with the service's environment through `sudo systemd-run --wait --pipe --uid=career-platform -p EnvironmentFile=/etc/career-platform/env -p WorkingDirectory=/opt/career-platform/app <command>` (called **run-as-app** below).

## Review Focus

1. **The app silently using the wrong database.** If `DATABASE_URL` is missing from the env file, Settings falls back to SQLite and the site looks fine but empty. Task 5 checks that the running service's database host is the RDS endpoint, and Task 6 compares rows through the app.
2. **TLS to RDS not verified.** `sslmode=prefer` would fall back without checking. Task 1 pins `sslmode=verify-full` with the CA bundle path in a test, and Task 6 confirms `ssl=on` from `pg_stat_ssl`.
3. **Links coming out as `http://` behind Nginx.** Uvicorn must trust `X-Forwarded-Proto` only from 127.0.0.1. Task 1 tests the unit's flags, and Task 7 checks a stylesheet URL on the page is `https://`.
4. **Reboot loses the site.** Services must be enabled, and the app must wait for the network. Task 8 reboots and checks.
5. **Port 22 or 5432 exposed wider than intended.** Task 3 and Task 4 check the security group rules after creation, and Task 8 rechecks them, plus `PubliclyAccessible=false`.

## Who does what

| Who | Does |
|---|---|
| Owner (console / browser) | Approves each settings table; attaches the IAM policy (G2); approves Cloudflare changes; signs in to `/admin` for write tests |
| Agent (laptop shell) | Runs AWS CLI, SSH, Cloudflare CLI, and repo changes after approval. If the permission check blocks a command that reads Railway secrets, the owner runs the exact command given, with `!` |

## Fixed names and values

| Item | Value |
|---|---|
| Tags on everything | `Project=career-platform` |
| SSH key | local `~/.ssh/career_platform_aws` (ed25519); AWS key pair `career-platform-aws` |
| Web security group | `career-platform-web`: 22 from owner IP `/32` (at planning `157.242.208.235`), 80 and 443 from `0.0.0.0/0` |
| DB security group | `career-platform-db`: 5432 from `career-platform-web` only; no egress rules |
| Instance | Name `career-platform-web`, subnet in `us-east-1a` (`subnet-0a8b5501bbf213822`) |
| DB subnet group | `career-platform-db-subnets`, all six default-VPC subnets |
| DB instance | `career-platform-db`, AZ `us-east-1a`, master user `career_platform`, database `career_platform` |
| Server user | system user `career-platform`, no login shell, home `/opt/career-platform` |
| Code | `/opt/career-platform/app` (git checkout of a pushed `aws-migration` commit); venv `/opt/career-platform/.venv` |
| Env file | `/etc/career-platform/env`, owner `root:career-platform`, mode `0640` |
| Snapshots | `/var/lib/career-platform/snapshots` (owned by `career-platform`) |
| RDS CA bundle | `/etc/ssl/certs/rds-global-bundle.pem` from `https://truststore.pki.rds.amazonaws.com/global/global-bundle.pem` |
| Test hostname | `aws.caelonk.me`, Cloudflare A record, DNS only (grey cloud) |

The app connects as the RDS master user. A separate least-privilege role is better practice; it's left out for this course deployment and listed in the README's limitations.

## Gates before anything is created

- [ ] **G1: Cost estimate.** Price EC2 `t3.small`, RDS `db.t4g.micro` Single-AZ, 20 GB gp3 RDS storage, 20 GB gp3 EBS, one public IPv4, RDS backup storage (free up to the DB size), and data transfer, from current us-east-1 prices, not memory. Compare the monthly total with the owner's credits and budget. Expected about $35/month (guide). Record it in the README "Costs, expiry and cleanup" section.
- [ ] **G2: Deployment policy review.** Walk the owner through `aws-ec2-deployment-policy.json`. It allows the EC2 and RDS actions this plan uses in us-east-1 (on any resource in the account), forces `t3.micro`/`t3.small`, IMDSv2, `db.t3.micro`/`db.t4g.micro`, Single-AZ, ≤20 GB encrypted storage, and enforces no budget. It has no SSM, IAM role, or Secrets Manager actions, which is why this plan uses SSH and a self-managed password. The owner creates policy `ISBA4775EC2Migration` and attaches it to `isba-student`. **Check:** `aws rds describe-db-engine-versions --engine postgres --query "DBEngineVersions[?starts_with(EngineVersion,'18')].EngineVersion"` succeeds and lists an 18.x version.

---

### Task 1: AWS deployment files in the repo

**Files:**
- Create: `deploy/aws/career-platform.service`
- Create: `deploy/aws/nginx-career-platform.conf`
- Create: `deploy/aws/env.example`
- Modify: `tests/operations/test_deployment_config.py` (add tests)
- Modify: `tests/test_config.py:11-19` (add one parametrize case)

**Interfaces:**
- Produces: the three files above, installed unchanged by Task 5 (`/etc/systemd/system/career-platform.service`, `/etc/nginx/sites-available/career-platform`, and the key list for `/etc/career-platform/env`).

- [ ] **Step 1: Write the failing tests** in `tests/operations/test_deployment_config.py`:

```python
def test_aws_unit_runs_as_service_user_behind_nginx():
    unit = Path("deploy/aws/career-platform.service").read_text()
    assert "User=career-platform" in unit
    assert "EnvironmentFile=/etc/career-platform/env" in unit
    assert "WorkingDirectory=/opt/career-platform/app" in unit
    assert "--host 127.0.0.1 --port 8000 --workers 2" in unit
    assert "--proxy-headers --forwarded-allow-ips 127.0.0.1" in unit
    assert "After=network-online.target" in unit
    assert "ReadWritePaths=/var/lib/career-platform" in unit
    assert "Restart=on-failure" in unit
    assert "WantedBy=multi-user.target" in unit


def test_aws_nginx_serves_test_host_only_and_proxies_locally():
    config = Path("deploy/aws/nginx-career-platform.conf").read_text()
    assert "server_name aws.caelonk.me;" in config
    assert "listen 80 default_server;" in config
    assert "return 404;" in config
    assert "proxy_pass http://127.0.0.1:8000;" in config
    assert "proxy_set_header X-Forwarded-Proto $scheme;" in config
    assert "client_max_body_size 1m;" in config


def test_aws_env_example_lists_keys_without_values():
    lines = Path("deploy/aws/env.example").read_text().splitlines()
    keys = {line.split("=", 1)[0] for line in lines if line and not line.startswith("#")}
    assert keys == {"ENVIRONMENT", "DATABASE_URL", "SECRET_KEY", "ADMIN_PASSWORD", "SNAPSHOT_DIR"}
    text = "\n".join(lines)
    assert "sslmode=verify-full" in text
    assert "sslrootcert=/etc/ssl/certs/rds-global-bundle.pem" in text
```

And add this case to the `test_normalize_database_url` parameters in `tests/test_config.py`:

```python
("postgresql://u:p@db.rds.amazonaws.com:5432/career_platform?sslmode=verify-full&sslrootcert=/etc/ssl/certs/rds-global-bundle.pem",
 "postgresql+psycopg://u:p@db.rds.amazonaws.com:5432/career_platform?sslmode=verify-full&sslrootcert=/etc/ssl/certs/rds-global-bundle.pem"),
```

- [ ] **Step 2: Run the tests to check the new ones fail**

Run: `.venv/Scripts/python.exe -m pytest tests/operations/test_deployment_config.py tests/test_config.py -q`
Expected: the three `test_aws_*` tests FAIL (file not found). The new normalize case passes already (it pins existing behavior).

- [ ] **Step 3: Write the three files.**
  - Unit: based on `deploy/systemd/career-platform.service`, with `Group=career-platform`, `ExecStart=/opt/career-platform/.venv/bin/uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8000 --workers 2 --proxy-headers --forwarded-allow-ips 127.0.0.1`, `RestartSec=3`, and hardening `NoNewPrivileges=true`, `ProtectSystem=strict`, `ProtectHome=true`, `PrivateTmp=true`, `ReadWritePaths=/var/lib/career-platform`.
  - Nginx: one port-80 server for `aws.caelonk.me` proxying to `127.0.0.1:8000` with the four `proxy_set_header` lines from the VM config and `client_max_body_size 1m;`, plus a `default_server` on port 80 with `server_name _;` returning 404. Certbot adds the 443 block in Task 7. A header comment says so.
  - `env.example`: the five keys. `ENVIRONMENT=production`, `SNAPSHOT_DIR=/var/lib/career-platform/snapshots`, `DATABASE_URL=postgresql://career_platform:<password>@<rds-endpoint>:5432/career_platform?sslmode=verify-full&sslrootcert=/etc/ssl/certs/rds-global-bundle.pem`, and `SECRET_KEY=` / `ADMIN_PASSWORD=` with comments saying where the values come from (Railway variables) and that they're never committed.

- [ ] **Step 4: Run the full suite**

Run: `.venv/Scripts/python.exe -m pytest -q`
Expected: all pass (skips for Postgres-only tests are fine).

- [ ] **Step 5: Commit and push the branch** (pushing `aws-migration` doesn't deploy; Railway watches `main`)

```bash
git add deploy/aws tests/operations/test_deployment_config.py tests/test_config.py
git commit -m "feat: add AWS EC2 systemd unit, Nginx site, and env template"
git push -u origin aws-migration
```

Record the pushed commit SHA. It's the commit Task 5 deploys.

---

### Task 2: Owner approves the EC2 and RDS settings

- [ ] **Step 1:** Show the owner the EC2 table (guide section 5) filled with this plan's values, and the console's Launch instance page for comparison. Wait for approval.
- [ ] **Step 2:** Show the RDS table filled with this plan's values, and the console's Create database page. Wait for approval.

Nothing is created in this task.

---

### Task 3: Create the web server (EC2)

**Interfaces:**
- Produces: instance ID, public IPv4, security group ID `WEB_SG` used by Task 4, and an SSH host entry used by Tasks 5–8.

- [ ] **Step 1:** Generate the key locally (`ssh-keygen -t ed25519 -f ~/.ssh/career_platform_aws -N ""`), then `aws ec2 import-key-pair --key-name career-platform-aws --public-key-material fileb://~/.ssh/career_platform_aws.pub` with tags.
- [ ] **Step 2:** Create `career-platform-web` in the default VPC (`vpc-0fd5d66b47b71cb35`) with ingress 22 from the owner's current IP `/32` (re-check with `curl -s https://checkip.amazonaws.com`), and 80 and 443 from `0.0.0.0/0`.
- [ ] **Step 3:** Re-resolve the latest Ubuntu 24.04 gp3 amd64 AMI from owner `099720109477`. Launch once with `run-instances`: `--instance-type t3.small`, `--credit-specification CpuCredits=standard`, `--metadata-options HttpTokens=required,HttpEndpoint=enabled`, `--block-device-mappings` for 20 GB gp3 `Encrypted=true,DeleteOnTermination=true`, `--subnet-id subnet-0a8b5501bbf213822`, `--associate-public-ip-address` via the network interface spec, key `career-platform-aws`, SG `career-platform-web`, and tags `Name=career-platform-web,Project=career-platform` on the instance and volume.
- [ ] **Step 4: Verify** with `describe-instances` and in the console: state `running`, type `t3.small`, `MetadataOptions.HttpTokens=required`, volume encrypted gp3 20 GB, one public IPv4, the one SG. `describe-security-groups` shows exactly the three ingress rules.
- [ ] **Step 5: SSH with host-key check.** Read the host key fingerprints from `aws ec2 get-console-output --latest` (between `BEGIN SSH HOST KEY FINGERPRINTS` lines). Connect as `ubuntu` and confirm the ED25519 fingerprint matches before accepting it. Add a `Host career-platform-aws` entry to `~/.ssh/config`.

---

### Task 4: Create the database (RDS)

**Interfaces:**
- Consumes: `WEB_SG` from Task 3.
- Produces: RDS endpoint hostname, and the DB password in a local file that Task 5 writes to the env file and then deletes.

- [ ] **Step 1:** Create SG `career-platform-db` (ingress tcp 5432 with source group `WEB_SG`; revoke the default all-traffic egress rule). Create subnet group `career-platform-db-subnets` with the six default subnets.
- [ ] **Step 2:** Generate the password locally into the session scratchpad: `python -c "import secrets; print(secrets.token_urlsafe(32), end='')" > db-password` (URL-safe characters only, so it works in a URL and meets RDS rules). Never `cat` it.
- [ ] **Step 3:** Pick the newest `18.x` from `describe-db-engine-versions`. Create once with `create-db-instance`: `--db-instance-identifier career-platform-db --engine postgres --engine-version <18.x> --db-instance-class db.t4g.micro --allocated-storage 20 --storage-type gp3 --storage-encrypted --no-multi-az --availability-zone us-east-1a --no-publicly-accessible --db-subnet-group-name career-platform-db-subnets --vpc-security-group-ids <DB_SG> --master-username career_platform --master-user-password "$(cat db-password)" --db-name career_platform --backup-retention-period 7 --deletion-protection --no-enable-performance-insights --monitoring-interval 0 --copy-tags-to-snapshot --tags Key=Project,Value=career-platform`. No `--max-allocated-storage`, so autoscaling stays off.
- [ ] **Step 4:** While it creates (5–10 minutes), start Task 5. Then `aws rds wait db-instance-available`.
- [ ] **Step 5: Verify** in CLI and console: status `available`, class `db.t4g.micro`, `MultiAZ=false`, `PubliclyAccessible=false`, `StorageEncrypted=true`, 20 GB gp3, `MaxAllocatedStorage` absent, `BackupRetentionPeriod=7`, SG ingress is only 5432 from `WEB_SG`. Record the endpoint.

---

### Task 5: Set up the server and deploy the app

**Interfaces:**
- Consumes: the Task 1 files at the pushed SHA, the RDS endpoint and password file from Task 4.
- Produces: `career-platform.service` active and enabled, serving on `127.0.0.1:8000`; Nginx serving `aws.caelonk.me` on port 80.

- [ ] **Step 1: Packages.** `apt update && apt upgrade -y`; install `nginx certbot python3-certbot-nginx git`; add the PostgreSQL apt repo (PGDG, official `apt.postgresql.org` instructions for noble) and install `postgresql-client-18`. Install uv 0.12.20 to `/usr/local/bin` with the pinned official installer. Check: `pg_restore --version` prints 18.x, `uv --version` prints 0.12.20, `python3 --version` prints 3.12.x.
- [ ] **Step 2: User and folders.** Create system user `career-platform` (no login shell, home `/opt/career-platform`). Create `/var/lib/career-platform/snapshots` and `/etc/career-platform` with the ownership in "Fixed names and values". Download the RDS CA bundle to `/etc/ssl/certs/rds-global-bundle.pem`.
- [ ] **Step 3: Code.** As `career-platform`, clone `https://github.com/caelonk/career-platform` into `/opt/career-platform/app`, check out the pushed SHA, run `UV_PROJECT_ENVIRONMENT=/opt/career-platform/.venv uv sync --locked --no-dev`. Check: `git -C /opt/career-platform/app rev-parse HEAD` equals the SHA.
- [ ] **Step 4: Env file, without printing secrets.** Write `ENVIRONMENT` and `SNAPSHOT_DIR` lines. Build `DATABASE_URL` on the laptop from the endpoint and `db-password` and send it through `ssh ... 'sudo tee -a /etc/career-platform/env >/dev/null'`. Copy `SECRET_KEY` and `ADMIN_PASSWORD` the same way: `railway variables --service career-platform --kv | grep -E '^(SECRET_KEY|ADMIN_PASSWORD)='` piped over SSH (owner runs it with `!` if the permission check blocks it). Then delete the local `db-password` file. Check: on the server, `sudo awk -F= '{print $1}' /etc/career-platform/env | sort` lists exactly the five keys; mode is `640 root:career-platform`.
- [ ] **Step 5: Install and start.** Copy the unit and Nginx site from the checkout; enable the site, remove `default`; `nginx -t`; `systemctl daemon-reload`; `systemctl enable --now career-platform nginx`. Don't run migrations yet; the database is empty until Task 6.
- [ ] **Step 6: Verify.** `systemctl is-enabled career-platform nginx` → `enabled` twice; `ps -o user= -C uvicorn` shows `career-platform`, never root. `curl -s localhost:8000/health` → `{"status":"ok"}`. `curl -s -o /dev/null -w '%{http_code}' -H 'Host: aws.caelonk.me' http://127.0.0.1/health` → 200, and with any other Host → 404. Check that the database host the app sees is the RDS endpoint: run-as-app `/opt/career-platform/.venv/bin/python -c "from app.config import get_settings; from sqlalchemy.engine import make_url; print(make_url(get_settings().database_url).host)"` (prints only the host). Also check `ADMIN_PASSWORD` arrived intact: run-as-app a one-liner that prints only `get_settings().admin_password.startswith('pbkdf2_sha256$200000$')` and its length compared with Railway's (owner runs `railway variables --service career-platform --kv | grep '^ADMIN_PASSWORD=' | wc -c`).

---

### Task 6: Restore the data into RDS

**Interfaces:**
- Consumes: `~/Downloads/backups/career_platform-<latest>.dump` and `career_platform-volume-<latest>.tar.gz` (take a fresh pair with the README procedure first if the latest is older than the last admin edit).
- Produces: RDS holding the Railway data at Alembic head; the snapshots folder restored.

- [ ] **Step 1:** Record the backup's per-table row counts by restoring it locally (README "Check a dump restores"). These are the expected numbers. Railway is not queried.
- [ ] **Step 2:** `scp` both files to `/tmp` on the server; check SHA-256 on both ends.
- [ ] **Step 3:** On the server, `sudo bash -c 'pg_restore --exit-on-error --no-owner --no-privileges -d "$(grep ^DATABASE_URL= /etc/career-platform/env | cut -d= -f2-)" /tmp/<dump>'`, so the URL is never shown (it's a plain `postgresql://` URL with no `$` in it, which libpq accepts as-is). Then run-as-app `/opt/career-platform/.venv/bin/alembic upgrade head`. Expected: no "Running upgrade" line; `alembic current` shows `20240917_initial_schema (head)`.
- [ ] **Step 4:** Extract the volume tar into `/var/lib/career-platform/` (giving `/var/lib/career-platform/snapshots/...`), `chown -R career-platform:`, then delete both files from `/tmp`.
- [ ] **Step 5: Verify.** Per-table counts on RDS equal Step 1's numbers for all 14 tables. `select ssl from pg_stat_ssl where pid = pg_backend_pid()` → `t`. Spot-check representative records: profile name, the 6 project slugs with published/featured flags. `systemctl restart career-platform`, then the home page through Nginx shows the same projects as `https://caelonk.me`.

---

### Task 7: Test hostname and HTTPS

**Interfaces:**
- Consumes: the instance's public IPv4.
- Produces: `https://aws.caelonk.me` with a Let's Encrypt certificate and HTTP→HTTPS redirect.

- [ ] **Step 1:** Save the zone's current records (`cf dns records list --zone caelonk.me`) to `docs/evidence/dns-before-aws.md`. Owner approves, then create one A record `aws` → instance IPv4, DNS only, TTL auto. No other record changes.
- [ ] **Step 2:** `dig +short aws.caelonk.me @1.1.1.1` returns the instance IP.
- [ ] **Step 3:** `sudo certbot --nginx -d aws.caelonk.me --redirect` with the owner's email for expiry notices. Then `sudo certbot renew --dry-run` succeeds, and `systemctl list-timers certbot.timer` shows the timer.
- [ ] **Step 4: Verify** from the laptop: `curl -sI http://aws.caelonk.me` → 301 to `https://`; `curl -s https://aws.caelonk.me/health` → ok; the home page HTML's stylesheet link starts with `https://aws.caelonk.me/static/`.

---

### Task 8: Verify on AWS and record evidence

**Files:**
- Create: `docs/evidence/aws-verification-2026-11.md`
- Modify: `README.md` (AWS section: what runs where, costs from G1, limitations, next step)

- [ ] **Step 1: Deployed commit.** `git rev-parse HEAD` on the server equals the pushed SHA.
- [ ] **Step 2: Data.** Counts and spot-checks from Task 6 recorded.
- [ ] **Step 3: Target-only record.** Owner signs in at `https://aws.caelonk.me/admin` and creates an unpublished project `aws-target-check`. `systemctl restart career-platform`; it's still there. (It's deleted before any cutover.)
- [ ] **Step 4: Reboot.** `sudo reboot`; after it's back, `/health` → ok, the home page lists the projects, and `systemctl is-active career-platform nginx` → `active`. If the public IPv4 changed, update the `aws` A record and note that it changed (input for Task 9).
- [ ] **Step 5: Pages and assets.** Home, each published project page, `/admin` login, a 404 page, `/static/` CSS and fonts, the resume file, HTTP→HTTPS redirect. The app has no uploads or outside integrations; say so.
- [ ] **Step 6: Security.** SG `career-platform-web` ingress is exactly 22 from one `/32`, plus 80 and 443. From the laptop, `nc -vz <ip> 8000` and `nc -vz <ip> 5432` fail. RDS: `PubliclyAccessible=false`, and SG ingress is only 5432 from `WEB_SG`. `ssh` with password auth is refused.
- [ ] **Step 7: Costs.** Billing → Credits and Cost Explorer for the last day; compare with G1.
- [ ] **Step 8:** Write each check's command, result, and date in the evidence file. Mark anything not verified. Update the README. Commit on `aws-migration` and push the branch.

---

### Task 9: Cutover (separate go, not required in class)

Only after Task 8 passes and the owner says go. Steps from guide section 8:

1. Allocate an Elastic IP and associate it with the instance (the auto-assigned IP changes on stop/start). Point `aws` at it.
2. Issue the `caelonk.me` certificate before moving traffic: `certbot certonly --manual --preferred-challenges dns -d caelonk.me`, adding the TXT record with `cf`. After cutover, re-issue with `certbot --nginx -d caelonk.me` so renewals run automatically over HTTP-01. Add `caelonk.me` to the Nginx `server_name`.
3. Save the current apex record, pause admin edits on Railway, take a final backup (README procedure).
4. Restore it into RDS (Task 6 steps, after dropping and recreating the `public` schema), compare counts, and drop the `aws-target-check` record.
5. Change only the apex record to the Elastic IP. The `www` redirect rule, mail, and other records stay.
6. Verify `https://caelonk.me` on AWS before making any admin edits there. Leave Railway running with no edits until DNS has propagated.

### Rollback

- **Before cutover:** nothing to undo on the live site. To abandon: delete the `aws` DNS record, terminate the instance, delete the RDS instance (turn off deletion protection; take a final snapshot), delete both SGs, the subnet group, and the key pair.
- **After cutover:** restore the saved apex record. If AWS accepted writes, dump RDS first and reconcile those rows into Railway before switching, because DNS doesn't move data.

### Cleanup at course end

Terminate the instance, release any Elastic IP, delete RDS with a final snapshot (a stopped RDS instance starts itself again after 7 days, so stopping isn't enough), delete the SGs, subnet group, key pair and DNS record, and check Billing for anything left. Run `aws logout --profile isba-4775`.
