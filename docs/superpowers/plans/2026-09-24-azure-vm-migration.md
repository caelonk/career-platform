# Azure VM Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Run the career platform on the existing Azure staging VM from a fresh GitHub clone and the laptop's SQLite data, confirm it serves that data, then deallocate the VM.

**Architecture:** One-off manual migration as `azureuser` into `~/career-platform` on the VM. Dependencies come from a committed `uv.lock`; data is the laptop's SQLite file copied with `scp` and checked by hash and row counts. Uvicorn listens on `127.0.0.1:8000` only and is reached from the laptop through an SSH tunnel, so no inbound ports beyond SSH are opened. Nginx, systemd, and PostgreSQL are out of scope (platform plan Task 8).

**Tech Stack:** Azure CLI, OpenSSH (`ssh`, `scp`), Ubuntu 24.04 `apt-get`, git, uv, Python 3.12 (VM) / 3.14 (laptop), SQLite 3, FastAPI + Uvicorn, Alembic.

**Spec:** The owner's migration outline (Server → Packages → Code → Python → Config → Data → Processes → Verify → Shutdown), `docs/superpowers/specs/2026-09-15-personal-career-platform-design.md`, and the as-built VM in `docs/superpowers/plans/2026-09-29-azure-vm-provisioning.md`.

## Facts this plan relies on (checked 2026-09-29, nothing changed)

| Fact | Value | Consequence |
|---|---|---|
| VM | `vm-career-platform` in `rg-career-platform`, **deallocated**, static public IP (look up with `az vm show -d … --query publicIps`) | Server step 2 starts it |
| SSH rule | `Allow-SSH-Laptop`, port 22 from the laptop's `/32` only | Server step 1 confirms the laptop still has that IP |
| Laptop IP | Must equal the SSH rule's source | Re-check on the day (Server 1) |
| GitHub repo | `https://github.com/caelonk/career-platform`, **public**, branch `main`, laptop in sync with `origin/main` | Clone over HTTPS with no credentials |
| Lock file | **`uv.lock` does not exist in the repo** | Python step 1 creates and pushes it before the VM can `uv sync` |
| uv on laptop | **Not installed** | Python step 1 installs it |
| SQLite data | `~/Downloads/career_platform.db` (94,208 bytes, 2026-09-24 14:06); `~/Downloads/Data/career_platform.db` is byte-identical | Copy the first one; nothing exists under the repo |
| sqlite3 CLI on laptop | Not installed; Python 3.14 is | Laptop-side DB checks use Python's `sqlite3` module |
| App entry point | `app.main:create_app` with `--factory` (the README's `app.main:app` does not exist) | Processes uses the factory form, like the systemd unit |
| Settings | `.env` keys `ENVIRONMENT`, `DATABASE_URL`, `SECRET_KEY`, `SNAPSHOT_DIR`, optional `ADMIN_PASSWORD` (pbkdf2 hash) | Config sets all five |
| Migrations | One revision, `20240917_initial_schema` | Data step checks the copied DB is at that revision |
| Auto-shutdown | 18:00 Pacific daily | Start by ~16:30 Pacific or the VM deallocates mid-migration |

## Global Constraints

- Every step names where it runs: **Laptop** (Git Bash in `~/career-platform` unless stated), **VM** (SSH session as `azureuser`), or **Portal**.
- Git Bash `az` commands are prefixed with `MSYS_NO_PATHCONV=1`.
- The laptop database file is never modified; it's the rollback copy.
- Uvicorn binds `127.0.0.1` only; no NSG rule is added or changed.
- Nothing is committed from the VM. `.env` is git-ignored, but `career_platform.db` is **not** (`.gitignore` only lists `db.sqlite3`), so `git status` on the VM will show it as untracked. That's expected; never `git add` on the VM.
- `SECRET_KEY` and the admin password on the VM aren't the repository defaults.
- Stop at any **Check** that doesn't match and report the output before continuing.

## Review Focus

1. **Laptop IP has changed since the SSH rule was written** → `ssh` times out, which looks like a broken VM. Server step 1 compares the two before anything else.
2. **`uv sync` without a lock file** → it fails or silently resolves new versions. Python step 1 creates `uv.lock`, and step 4 uses `--locked` so drift fails loudly.
3. **Wrong or half-copied database** (the Downloads copy vs. something else, or a truncated `scp`) → site shows empty or stale content. Data steps compare SHA-256 and per-table row counts on both sides.
4. **Public-repo default secrets in use** (`SECRET_KEY=change-me-in-development`, the committed default admin hash) → anyone reading GitHub can forge sessions or log in. Config steps replace both and check they differ.
5. **Uvicorn reachable from the internet or left running after shutdown** → Processes binds loopback and checks `ss`; Shutdown stops it before deallocating.

---

## Server

- [x] **Server 1: Confirm the laptop IP still matches the SSH rule**
  - **Where:** Laptop
  - **Run:**
    ```bash
    LAPTOP_IP=$(curl -4 -s https://api.ipify.org); echo "$LAPTOP_IP"
    MSYS_NO_PATHCONV=1 az network nsg rule show -g rg-career-platform --nsg-name vm-career-platformNSG -n Allow-SSH-Laptop --query sourceAddressPrefix -o tsv
    ```
  - **Why:** SSH is allowed only from one `/32`. A new network (home, campus, hotspot) means a new IP and a silent timeout.
  - **Check:** First line + `/32` equals the second line (e.g. `203.0.113.10` and `203.0.113.10/32`).
  - **If it differs:** `MSYS_NO_PATHCONV=1 az network nsg rule update -g rg-career-platform --nsg-name vm-career-platformNSG -n Allow-SSH-Laptop --source-address-prefixes <new-ip>/32`
  - **Undo:** Read-only. If you updated the rule, set it back with the same command and the old IP.

- [x] **Server 2: Start the VM**
  - **Where:** Laptop (or Portal: *Virtual machines → vm-career-platform → Start*)
  - **Run:** `az vm start -g rg-career-platform -n vm-career-platform`
  - **Why:** The VM is deallocated; compute billing starts now (~$0.0094/hr).
  - **Check:** `az vm show -d -g rg-career-platform -n vm-career-platform --query "[powerState, publicIps]" -o tsv` prints `VM running` and the public IP. Save it for later steps: `VM_IP=$(az vm show -d -g rg-career-platform -n vm-career-platform --query publicIps -o tsv)`
  - **Undo:** `az vm deallocate -g rg-career-platform -n vm-career-platform`

- [x] **Server 3: Get the VM's SSH host key fingerprint out-of-band**
  - **Where:** Laptop
  - **Run:**
    ```bash
    MSYS_NO_PATHCONV=1 az vm run-command invoke -g rg-career-platform -n vm-career-platform --command-id RunShellScript --scripts "ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub" --query "value[0].message" -o tsv
    ```
  - **Why:** The first `ssh` asks you to trust a fingerprint. Getting it through Azure's control plane lets you compare instead of blindly typing `yes`.
  - **Check:** Output contains a line starting `256 SHA256:` — note it.
  - **Undo:** Read-only.

- [x] **Server 4: Open an SSH session**
  - **Where:** Laptop
  - **Run:** `ssh -i ~/.ssh/isba4775_azure azureuser@$VM_IP`
  - **Why:** All VM steps below run in this session.
  - **Check:** The fingerprint prompt matches Server 3; answer `yes`. Then `whoami; lsb_release -ds` prints `azureuser` and `Ubuntu 24.04.x LTS`.
  - **Undo:** `exit`. To forget the host key: `ssh-keygen -R $VM_IP` on the laptop.

## Packages

- [x] **Packages 1: Record what's already installed**
  - **Where:** VM
  - **Run:** `dpkg-query -W -f='${Package} ${Status}\n' git sqlite3 2>&1 | tee ~/packages-before.txt`
  - **Why:** Undo should only remove what this migration added; git ships with the Azure Ubuntu image.
  - **Check:** File exists; typically `git install ok installed` and `sqlite3` reported as not installed.
  - **Undo:** `rm ~/packages-before.txt`

- [x] **Packages 2: Install git and sqlite3**
  - **Where:** VM
  - **Run:** `sudo apt-get update && sudo apt-get install -y git sqlite3`
  - **Why:** git to clone; sqlite3 to inspect the copied database.
  - **Check:** `git --version && sqlite3 --version` both print versions.
  - **Undo:** For each package **not** installed in `~/packages-before.txt`: `sudo apt-get remove -y sqlite3` (and `git` only if it was absent before).

## Code

- [x] **Code 1: Clone the repository**
  - **Where:** VM
  - **Run:** `git clone https://github.com/caelonk/career-platform.git ~/career-platform && cd ~/career-platform`
  - **Why:** Get the exact code on `main`; the repo is public, so no credentials are needed on the VM.
  - **Check:** `git log -1 --oneline` on the VM matches `git log -1 --oneline origin/main` on the laptop, and `ls` shows `app migrations pyproject.toml`.
  - **Undo:** `rm -rf ~/career-platform`

## Python

- [x] **Python 1: Create the lock file and push it**
  - **Where:** Laptop (PowerShell for the install, then Git Bash)
  - **Run:**
    ```powershell
    winget install --id astral-sh.uv -e
    ```
    ```bash
    uv --version
    uv lock
    git add uv.lock
    git commit -m "build: add uv lock file"
    git push origin main
    ```
  - **Why:** The repo has no `uv.lock`, so "uv sync from the lock file" isn't possible yet. Locking on the laptop pins the versions you've tested against.
  - **Check:** `git ls-files uv.lock` prints `uv.lock`; `git status -sb` shows `## main...origin/main` with nothing ahead. Note the `uv --version` output for Python 2.
  - **Undo:** `git revert <commit>` and push; `winget uninstall --id astral-sh.uv`.

- [x] **Python 2: Install uv on the VM**
  - **Where:** VM
  - **Run (replace `X.Y.Z` with the laptop's `uv --version`):** `curl -LsSf https://astral.sh/uv/X.Y.Z/install.sh | sh && source ~/.local/bin/env`
  - **Why:** Same uv version on both sides reads the lock file the same way.
  - **Check:** `uv --version` matches the laptop.
  - **Undo:** `rm -f ~/.local/bin/uv ~/.local/bin/uvx && rm -rf ~/.local/share/uv ~/.cache/uv`, and remove the line the installer added to `~/.bashrc`/`~/.profile`.

- [x] **Python 3: Pull the lock file**
  - **Where:** VM, in `~/career-platform`
  - **Run:** `git pull --ff-only`
  - **Why:** Code 1 cloned before the lock was pushed.
  - **Check:** `ls uv.lock` succeeds; `git log -1 --oneline` shows `build: add uv lock file`.
  - **Undo:** `git reset --hard <commit from Code 1>`.

- [x] **Python 4: Install dependencies from the lock**
  - **Where:** VM, in `~/career-platform`
  - **Run:** `uv sync --locked --no-dev --python 3.12`
  - **Why:** `--locked` refuses to run if `uv.lock` and `pyproject.toml` disagree; `--no-dev` skips test tooling; 3.12 is Ubuntu's system Python and within `requires-python`.
  - **Check:** `.venv/bin/python --version` prints `Python 3.12.x`; `.venv/bin/python -c "import fastapi, sqlalchemy, alembic, uvicorn; print('ok')"` prints `ok`.
  - **Undo:** `rm -rf .venv`

## Config

- [x] **Config 1: Copy the example**
  - **Where:** VM, in `~/career-platform`
  - **Run:** `cp .env.example .env && chmod 600 .env`
  - **Why:** Start from the documented keys; `600` keeps the secret readable only by `azureuser`.
  - **Check:** `stat -c '%a %n' .env` prints `600 .env`; `git status --short` prints nothing (`.env` is ignored).
  - **Undo:** `rm .env`

- [x] **Config 2: Set environment, paths, and a real secret key**
  - **Where:** VM, in `~/career-platform`
  - **Run:**
    ```bash
    sed -i "s|^ENVIRONMENT=.*|ENVIRONMENT=staging|" .env
    sed -i "s|^DATABASE_URL=.*|DATABASE_URL=sqlite:////home/azureuser/career-platform/career_platform.db|" .env
    sed -i "s|^SNAPSHOT_DIR=.*|SNAPSHOT_DIR=/home/azureuser/career-platform/snapshots|" .env
    sed -i "s|^SECRET_KEY=.*|SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_urlsafe(48))')|" .env
    ```
  - **Why:** Absolute paths don't depend on the working directory. `staging` matches the VM's tag and keeps session cookies usable over the plain-HTTP tunnel (`production` sets `Secure` cookies). The example secret is public on GitHub.
  - **Check:** `.venv/bin/python -c "from app.config import get_settings as g; s=g(); print(s.environment, s.database_url, s.snapshot_dir, len(s.secret_key) > 40 and 'change-me' not in s.secret_key)"` prints `staging sqlite:////home/azureuser/career-platform/career_platform.db /home/azureuser/career-platform/snapshots True`.
  - **Undo:** `cp .env.example .env` (or `rm .env`).

- [x] **Config 3: Replace the default admin password**
  - **Where:** VM, in `~/career-platform`
  - **Run:**
    ```bash
    echo "ADMIN_PASSWORD=$(.venv/bin/python -c 'import getpass; from app.services.auth import hash_password; print(hash_password(getpass.getpass("New admin password: ")))')" >> .env
    ```
  - **Why:** Without it the app falls back to the hash committed in `app/config.py`, which is public.
  - **Check:** `.venv/bin/python -c "from app.config import get_settings as g, Settings; print(g().admin_password != Settings.model_fields['admin_password'].default)"` prints `True`. Store the password in your password manager.
  - **Undo:** `sed -i '/^ADMIN_PASSWORD=/d' .env`

## Data

- [x] **Data 1: Confirm the laptop copy is quiet and fingerprint it** — *Done 2026-09-29: file passed integrity check but had **no tables** (a byproduct of a local test run). Owner chose to start from an empty schema.*
  - **Where:** Laptop
  - **Run:**
    ```bash
    ls ~/Downloads/career_platform.db-wal ~/Downloads/career_platform.db-journal 2>&1
    sha256sum ~/Downloads/career_platform.db
    python -c "import sqlite3; c=sqlite3.connect('file:' + __import__('os').path.expanduser('~/Downloads/career_platform.db').replace(chr(92), '/') + '?mode=ro', uri=True); print(c.execute('pragma integrity_check').fetchone()[0], c.execute('select version_num from alembic_version').fetchone()[0]); [print(t, c.execute(f'select count(*) from {t}').fetchone()[0]) for (t,) in c.execute(\"select name from sqlite_master where type='table' order by name\")]" | tee ~/db-laptop-counts.txt
    ```
  - **Why:** A `-wal`/`-journal` file means something has the DB open and the main file may be incomplete. The hash and counts are what the VM copy must match. `mode=ro` guarantees the laptop file isn't touched.
  - **Check:** Both `ls` calls report `No such file`; first line of counts is `ok 20240917_initial_schema`; note the hash.
  - **Undo:** Read-only. `rm ~/db-laptop-counts.txt`.

- [x] **Data 2: Make sure nothing on the VM would be overwritten**
  - **Where:** VM, in `~/career-platform`
  - **Run:** `ls -l career_platform.db 2>&1`
  - **Why:** `scp` overwrites silently.
  - **Check:** `No such file or directory`. If a file exists, stop and find out why before continuing.
  - **Undo:** Read-only.

- [x] ~~**Data 3: Copy the database**~~ — *Not run: nothing to copy. Replaced by `.venv/bin/alembic upgrade head` on the VM, then the owner's resume content was loaded by a one-off script (not committed) in one transaction.*
  - **Where:** Laptop
  - **Run:** `scp -i ~/.ssh/isba4775_azure ~/Downloads/career_platform.db azureuser@$VM_IP:/home/azureuser/career-platform/career_platform.db`
  - **Why:** Moves the data; the laptop original stays as the rollback copy.
  - **Check:** Transfer reports `100%` and 94 KB.
  - **Undo:** On the VM: `rm ~/career-platform/career_platform.db`.

- [x] **Data 4: Prove the copy matches** — *Done differently: `alembic current` = `20240917_initial_schema (head)`, integrity `ok`; row counts checked after the content load instead of against the laptop file.*
  - **Where:** VM, in `~/career-platform`
  - **Run:**
    ```bash
    chmod 600 career_platform.db
    sha256sum career_platform.db
    echo "$(sqlite3 career_platform.db 'pragma integrity_check') $(sqlite3 career_platform.db 'select version_num from alembic_version')"
    for t in $(sqlite3 career_platform.db "select name from sqlite_master where type='table' order by name"); do echo "$t $(sqlite3 career_platform.db "select count(*) from $t")"; done
    .venv/bin/alembic current
    ```
  - **Why:** Same hash = byte-identical; counts and revision confirm the app will read the same content without needing a migration.
  - **Check:** Hash equals Data 1's; the count lines equal `~/db-laptop-counts.txt` line for line; `alembic current` prints `20240917_initial_schema (head)`.
  - **Undo:** `rm career_platform.db` and repeat Data 3.

## Processes

- [x] **Processes 1: Start Uvicorn on loopback**
  - **Where:** VM, in `~/career-platform`
  - **Run:**
    ```bash
    nohup .venv/bin/uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8000 > ~/uvicorn.log 2>&1 &
    echo $! > ~/uvicorn.pid
    ```
  - **Why:** Runs the app the same way the future systemd unit will, survives closing the SSH session, and listens only on loopback.
  - **Check:** After ~3 seconds, `ss -ltnp | grep ':8000'` shows `127.0.0.1:8000` (not `0.0.0.0`), and `tail -n 5 ~/uvicorn.log` contains `Application startup complete`.
  - **Undo:** `kill "$(cat ~/uvicorn.pid)" && rm ~/uvicorn.pid`

## Verify

### Results (2026-09-29)

| # | Check | Where | Command | Expected | Actual | Result |
|---|---|---|---|---|---|---|
| 1a | App health | VM | `curl -fsS http://127.0.0.1:8000/health` | `{"status":"ok"}` | `{"status":"ok"}` | Pass |
| 1b | Profile on home page | VM | `curl -fsS http://127.0.0.1:8000/ \| grep -c "$NAME"` | ≥ 1 | 2 (page title and heading) | Pass |
| 1c | Featured project | VM | Home page `Featured project` section | Technician Dispatch Dashboard | Technician Dispatch Dashboard | Pass |
| 1d | Phone not published | VM | `curl -fsS http://127.0.0.1:8000/ \| grep -c "<phone>"` | 0 | 0 | Pass |
| 2a | Published project pages | VM | `curl -w '%{http_code}' …/projects/<slug>` for each published slug | 4 × `200` | 4 × `200` | Pass |
| 2b | Unknown or draft slug hidden | VM | `curl -w '%{http_code}' …/projects/not-a-real-project` | `404` | `404` | Pass |
| 3a | Pages in browser via tunnel | Laptop | `http://localhost:8000` over `ssh -L 8000:127.0.0.1:8000` | Profile, featured project, 4 projects | Confirmed by owner | Pass |
| 3b | Admin login | Laptop | `POST /auth/login` as `admin`, then `GET /admin` with cookie | `303` → `/admin`, then `200` | `303` → `/admin`, `200` | Pass |
| 3c | Wrong password rejected | Laptop | `POST /auth/login` with a wrong password | `303` → `/auth/login?error=invalid` | `303` → `/auth/login?error=invalid` | Pass |
| 3d | App not exposed publicly | Laptop | `curl http://$VM_IP:8000/health` | Connection fails (only SSH allowed) | Timed out | Pass |

- [x] **Verify 1: Health and home page on the VM**
  - **Where:** VM
  - **Run:**
    ```bash
    curl -fsS http://127.0.0.1:8000/health; echo
    NAME=$(sqlite3 ~/career-platform/career_platform.db "select name from profiles limit 1")
    curl -fsS http://127.0.0.1:8000/ | grep -c "$NAME"
    ```
  - **Why:** Confirms the app answers and renders from the copied database, not an empty one or the snapshot fallback.
  - **Check:** `{"status":"ok"}`, then a count of `1` or more.
  - **Undo:** Read-only.

- [x] **Verify 2: Every published project page renders** — *Done 2026-09-29: 4 published project pages returned 200; an unknown slug returned 404.*
  - **Where:** VM
  - **Run:**
    ```bash
    for s in $(sqlite3 ~/career-platform/career_platform.db "select slug from projects where publication_status='published'"); do echo "$s $(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/projects/$s)"; done
    for s in $(sqlite3 ~/career-platform/career_platform.db "select slug from projects where publication_status<>'published'"); do echo "$s $(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/projects/$s)"; done
    ```
  - **Why:** Published data is visible and drafts stay hidden after the move.
  - **Check:** First loop is all `200`; second loop is all `404` (or prints nothing if there are no drafts).
  - **Undo:** Read-only.

- [x] **Verify 3: See it in your browser through a tunnel** — *Done 2026-09-29: owner confirmed pages; admin login (username `admin`) verified through the tunnel.*
  - **Where:** Laptop (new Git Bash window), then browser
  - **Run:** `VM_IP=$(az vm show -d -g rg-career-platform -n vm-career-platform --query publicIps -o tsv); ssh -i ~/.ssh/isba4775_azure -N -L 8000:127.0.0.1:8000 azureuser@$VM_IP`, then open `http://localhost:8000`
  - **Why:** A visual check of your data without opening ports 80/443.
  - **Check:** Page shows your name, headline, and published projects; logging in at the admin page works with the Config 3 password.
  - **Undo:** `Ctrl+C` in the tunnel window.

## Shutdown

- [x] **Shutdown 1: Stop Uvicorn** — *Done 2026-09-29: Uvicorn logged a clean shutdown; nothing listening on :8000.*
  - **Where:** VM
  - **Run:** `kill "$(cat ~/uvicorn.pid)" && rm ~/uvicorn.pid`
  - **Why:** Clean stop so SQLite isn't mid-write when the disk goes cold.
  - **Check:** `ss -ltn | grep ':8000'` prints nothing.
  - **Undo:** Repeat Processes 1.

- [x] **Shutdown 2: Close the session and tunnel** — *Done 2026-09-29: tunnel closed; no local listener on :8000.*
  - **Where:** Laptop
  - **Run:** `exit` in the SSH session; `Ctrl+C` in the tunnel window.
  - **Check:** Laptop prompt returns in both windows.
  - **Undo:** Server 4.

- [x] **Shutdown 3: Deallocate the VM** — *Done 2026-09-29: `VM deallocated`; static public IP retained.*
  - **Where:** Laptop (or Portal: *vm-career-platform → Stop*, which deallocates)
  - **Run:** `az vm deallocate -g rg-career-platform -n vm-career-platform`
  - **Why:** Stops compute billing. `az vm stop` would keep billing.
  - **Check:** `az vm show -d -g rg-career-platform -n vm-career-platform --query powerState -o tsv` prints `VM deallocated`. The public IP stays the same (static), and the disk keeps the code, `.env`, and database for next time.
  - **Undo:** `az vm start -g rg-career-platform -n vm-career-platform`

---

## Full rollback

Everything the migration created on the VM can be removed without touching Azure resources, from an SSH session:

```bash
pkill -f "uvicorn app.main:create_app" || true
rm -rf ~/career-platform ~/uvicorn.log ~/uvicorn.pid ~/packages-before.txt
rm -f ~/.local/bin/uv ~/.local/bin/uvx && rm -rf ~/.local/share/uv ~/.cache/uv
```

Then remove `sqlite3` per Packages 2 and revert the `uv.lock` commit only if you don't want to keep it. The laptop database is never modified, so it's always the source of truth.

## Execution record (2026-09-29, inline)

- Server 4: the host key was trusted without typing `yes`. The `ssh-keyscan` fingerprint was compared to Server 3's, added to `known_hosts` only on a match, and every later connection used `StrictHostKeyChecking=yes`.
- Python 1: `uv.lock` committed and pushed as `37cd185` (uv 0.12.20, 37 packages).
- Config 3: a random admin password was generated on the VM. Only its hash is stored in `.env`.
- Data: the laptop database was empty, so the schema was created with Alembic and content was loaded from the owner's resume (phone omitted). The regenerated public snapshot (name and project summaries only) was committed as `6968ad7`.
- Processes 1: `< /dev/null` was added to the `nohup` command so the non-interactive SSH session could return.
- Shutdown 2: stopping the background tunnel task left its `ssh.exe` listening on :8000, so that exact process was ended.
- All 25 steps are complete. The VM is deallocated.

## Self-review

- **Outline coverage:** all nine owner categories appear as sections, in the given order; each step lists where, what, why, check, and undo.
- **Gaps found and closed:** missing `uv.lock` (Python 1), deallocated VM (Server 2), SSH source-IP lock (Server 1), public default secrets (Config 2–3), no sqlite3 on laptop (Data 1 uses Python), README entry point wrong (Processes 1 uses `--factory`), and seeing the site without opening web ports (Verify 3 tunnel).
- **Not in scope:** systemd, Nginx, TLS, PostgreSQL, the `career-platform` service user. Those belong to `2026-09-29-azure-vm-provisioning.md` and platform plan Task 8; when they land, the app moves from `~/career-platform` to `/srv/career-platform`.
