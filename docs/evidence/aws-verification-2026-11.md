# AWS test copy: verification (plan Task 8)

Plan: [`docs/superpowers/plans/2026-11-01-aws-ec2-rds-migration.md`](../superpowers/plans/2026-11-01-aws-ec2-rds-migration.md).
Checks run 2026-11-02 (UTC) against `https://aws.caelonk.me`. `caelonk.me` was still on
Railway throughout.

## What was built

| Part | Value |
|---|---|
| EC2 | `i-06048d44c1c4f3a12` `career-platform-web`, `t3.small`, `us-east-1a`, Ubuntu 24.04.5 (`ami-0d6dd9e8265d48906`), Standard CPU credits, IMDSv2 required, 20 GB gp3 encrypted, public IPv4 `184.196.73.49` (auto-assigned), private `172.31.0.170` |
| Web security group | `sg-0cdb0326959e0d462` `career-platform-web`: 22 from `157.242.208.235/32`, 80 and 443 from `0.0.0.0/0` |
| RDS | `career-platform-db`, PostgreSQL 18.6, `db.t4g.micro`, Single-AZ `us-east-1a`, 20 GB gp3 encrypted, no autoscaling, not publicly accessible, backups 1 day (Free plan maximum, see below), deletion protection on, CA `rds-ca-rsa2048-g1` |
| DB security group | `sg-059707e5ae5fca876` `career-platform-db`: 5432 from `sg-0cdb0326959e0d462` only, no egress rules |
| App | Commit `3199197` at `/opt/career-platform/app`; systemd `career-platform.service` as user `career-platform`, Uvicorn 2 workers on `127.0.0.1:8000`; Nginx in front; env in `/etc/career-platform/env` (`640 root:career-platform`) |
| DNS | Cloudflare A `aws.caelonk.me` → `184.196.73.49`, DNS only. Records before: [`dns-before-aws.md`](dns-before-aws.md) |
| Certificate | Let's Encrypt (YE1) for `aws.caelonk.me`, expires 2027-01-30, renewed by `certbot.timer` |

## Checks

| # | Check | How | Result |
|---|---|---|---|
| 1 | Deployed commit | `git rev-parse HEAD` on the server vs `origin/aws-migration` | Both `3199197ae8ee…` ✅ |
| 2 | Data matches the backup | Fresh backup `career_platform-20261102-004102Z.dump` restored locally for expected numbers, then into RDS from the server; per-table counts, project slugs with published/featured flags, profile name | All 14 tables, 6 projects and the profile identical ✅. Railway wasn't queried for the comparison |
| 2b | Migrations | `alembic upgrade head` then `alembic current` | No upgrade ran; `20240917_initial_schema (head)` ✅ |
| 2c | TLS to RDS | `pg_stat_ssl` for the session; app settings | `ssl=true`, TLSv1.3; app uses `sslmode=verify-full` with the RDS CA bundle ✅ |
| 2d | App uses RDS, not SQLite | Settings read through systemd with the service's env file | Host is the RDS endpoint; `is_production` true; `ADMIN_PASSWORD` hash 90 chars, same as Railway ✅ |
| 3 | Target-only record survives restart | Owner created unpublished project `aws-target-check` in `/admin` on AWS; `systemctl restart career-platform` | Row id 7 present before and after restart; not on the public home page ✅. To be deleted before cutover |
| 4 | Reboot | `systemctl reboot` | Booted 00:48:30; `career-platform` and `nginx` active; `/health` ok; home lists 5 published projects; public IP unchanged ✅ |
| 5 | Pages and assets | `curl` against AWS and `https://caelonk.me` | Home, all 5 project pages, `/auth/login`, `/admin` → 303 to login, 404 page (HTML for browsers), `site.css`, both fonts, `/static/favicon.svg`, `/resume.pdf` (same SHA-256 as live) all match live ✅ |
| 5b | HTTPS and redirects | `curl -I http://aws.caelonk.me/`; page HTML | 301 to `https://`; certificate verifies; stylesheet link is `https://aws.caelonk.me/static/css/site.css` ✅. `www.caelonk.me` still redirects to `https://caelonk.me` (unchanged) |
| 5c | Uploads and integrations | Code review | The app has no file uploads and no outside integrations; nothing to test |
| 5d | Certificate renewal | `certbot renew --dry-run`; `systemctl is-enabled certbot.timer` | Simulated renewal succeeded; timer enabled ✅ |
| 6 | Restricted SSH | Security group rules; password login attempt; `sshd -T` | Port 22 only from one `/32`; password login refused (`publickey` only); `passwordauthentication no` ✅ |
| 6b | RDS private | `describe-db-instances`; endpoint DNS; TCP from laptop | `PubliclyAccessible=false`; endpoint resolves to `172.31.6.214`; laptop → RDS:5432 blocked ✅ |
| 6c | No extra ports | TCP from laptop to the server | 8000, 5432, 3306, 25 blocked ✅ |
| 6d | IMDSv2 | Metadata request without a token, on the server | 401 ✅ |
| 7 | Cost | Owner, Billing → Credits | $0 so far (2026-11-02). Charges can lag by a day |

## Deviations from the plan

- **RDS backup retention is 1 day, not 7.** The Free plan refused 2–7 days
  (`FreeTierRestrictionError`), and the guide forbids upgrading. Weekly manual dumps to the
  laptop and Google Drive (README "Backup record") keep the 1-week RPO.
- Certbot was registered without an email address; Let's Encrypt no longer sends expiry
  emails, and the renewal timer is tested.

## Not verified

- Behaviour when RDS is down (the home page's 503 path) was not tested on AWS.
- Billing for the first full day hadn't appeared yet.
