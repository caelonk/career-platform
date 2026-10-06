# Operate the VM Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the career platform run like a real website. Visitors reach `http://52.162.50.66` with no port number, and the app starts at boot, comes back after a crash, and survives one worker crashing.

**Architecture:** Nginx listens on port 80 and is the only program visitors reach. It passes each request (reverse proxy) to Uvicorn on `127.0.0.1:8000`, which runs the existing app from `~/career-platform` with two worker processes. systemd starts Uvicorn at boot and restarts it if it dies, running it as `azureuser`. The Azure firewall (NSG) allows port 22 from my laptop and port 80 from anyone. Port 8000 never opens.

**Tech Stack:** Ubuntu 24.04, systemd, Nginx (Ubuntu package), Uvicorn 0.54 with `--workers 2`, FastAPI (`app.main:create_app --factory`), SQLite, Azure NSG, Cloudflare DNS.

**Spec:** Session 10, "Operate your site on the VM" (course handout, not stored in this repo). Its requirements, restated:
- the site answers at `http://PUBLIC-IP` without a port
- it starts at boot and restarts after a crash
- one crash doesn't take the whole site down
- port 8000 stays closed to the Internet
- the app doesn't run as root
- the service is named `career-platform`
- the existing code, Python environment, and database in `~/career-platform` are used as-is

## VM details (looked up with the Azure CLI, read-only)

| Item | Value |
|---|---|
| VM | `vm-career-platform` (the only VM in the subscription) |
| Resource group | `rg-career-platform` |
| Region / size | `northcentralus` / `Standard_B2ats_v2` (2 vCPU, 1 GiB) |
| OS / admin user | Ubuntu 24.04 LTS / `azureuser` |
| Public IP | `52.162.50.66`. Static, Standard SKU, so it survives deallocation |
| Private IP | `10.0.0.4` |
| SSH | `ssh -i ~/.ssh/isba4775_azure azureuser@52.162.50.66` |
| NSG rules today | `Allow-SSH-Laptop`: TCP 22 from my laptop's `/32`, priority 300. Tuesday's temporary port-8000 rule is already deleted |
| Auto-shutdown | 18:00 Pacific, daily |
| App on the VM | `~/career-platform`: code at `origin/main`, `.venv` (Python 3.12), `.env`, `career_platform.db` with my data |

## The picture

```
Internet
   │
Public IP 52.162.50.66            (Azure holds this; the VM only sees 10.0.0.4)
   │
NSG: 22 from my laptop · 80 from anyone · nothing else
   │
Ubuntu VM
   ├── sshd                      0.0.0.0:22
   └── Nginx                     0.0.0.0:80   ← the front door
          │ proxy_pass
          ▼
       Uvicorn main process      127.0.0.1:8000  (run by systemd as azureuser)
          ├── worker 1  ─┐
          └── worker 2  ─┴──▶ ~/career-platform/career_platform.db
```

| Program | Job | If it dies |
|---|---|---|
| Nginx | Takes every request from the Internet and hands it to Uvicorn | Visitors get no answer. systemd restarts Nginx too |
| Uvicorn main process | Starts the workers and replaces any that die | systemd restarts it (`Restart=on-failure`) |
| Uvicorn workers (2) | Run the Python app and answer requests | The main process starts a new one; the other keeps serving |
| systemd | Starts Uvicorn at boot (`enable`) and after a crash (`Restart=`) | — |

## Global Constraints

- Port 8000 is never opened in the NSG. Uvicorn binds `127.0.0.1` only.
- The app runs as `azureuser`, never root.
- No files in the repo change, and no tests are added. The repo's `deploy/systemd/career-platform.service` (user `career-platform`, `/srv` paths) and `deploy/nginx/career-platform.conf` (HTTPS with certificates that don't exist yet) are **not** used today.
- Everything in the Azure portal, Cloudflare, and Namecheap is done by me, not the agent: VM start, restart, and stop, the `Allow-HTTP-80` rule, and DNS.
- Crash and restart tests are run by me. The plan only records their evidence.
- The systemd service is named `career-platform`.
- This plan file never contains my laptop's IP or the Azure subscription ID.

## Review Focus

1. **Wrong working directory.** The app loads `.env` relative to the folder it starts in (`app/config.py`). Started anywhere else, it falls back to the default SQLite path and shows the demo or snapshot content instead of mine. Pinned by Service step 3's "Caelon King" check.
2. **Nginx default site shadows mine.** The package enables a welcome page on port 80. Pinned by Front door step 4: `ls /etc/nginx/sites-enabled` shows only `career-platform`, and the page contains my name.
3. **Uvicorn bound to `0.0.0.0`.** Visitors could skip Nginx. Pinned by Service step 3 and Front door step 4: `ss` shows `127.0.0.1:8000`.
4. **Started but not enabled.** The site works today and is gone after a reboot. Pinned by Service step 3: `systemctl is-enabled` → `enabled`, and by Restart evidence.
5. **Leftover hand-started Uvicorn on 8000.** The service fails with "Address already in use." Pinned by Preflight step 2: nothing on 8000 before the service starts.

---

## 1. Preflight

**What this is:** The VM was fully off (deallocated). When it's off, memory is wiped and every running program ends, but the disk keeps every file. This section proves both: the files are there, and the site isn't running. That gap is why we need a service.

- [x] **Preflight 1: Start the VM after it was fully off**
  - **Where:** Portal (me)
  - **Run:** VM Overview. If it's Running, Stop and wait for "Stopped (deallocated)". Then Start.
  - **Why:** Proves what survives a full power-off.
  - **Check:** Status says Running. From the laptop, `ssh -i ~/.ssh/isba4775_azure azureuser@52.162.50.66 'hostname'` prints `vm-career-platform`. If SSH hangs, my laptop's IP changed, so I update `Allow-SSH-Laptop`'s source in the portal.
  - **Undo:** Stop the VM in the portal.

- [x] **Preflight 2: Files are there, nothing is listening**
  - **Where:** VM
  - **Run:**
    ```bash
    ls ~/career-platform
    curl -sS http://127.0.0.1:8000 ; echo "exit=$?"
    sudo ss -ltnp
    ```
  - **Why:** The disk kept the code, `.env`, and database. The hand-started Uvicorn lived in memory and is gone.
  - **Check:** `ls` shows `app`, `career_platform.db`, `.venv` is present; `curl` says `Connection refused` (exit 7); `ss` shows nothing on `:8000` or `:80`, only `:22` and `127.0.0.53:53`.
  - **Undo:** Read-only.

**Results (2026-10-05):**

| Check | Expected | Actual | Result |
|---|---|---|---|
| VM state before start | Fully off | `VM deallocated`; I started it in the portal, now `VM running` | Pass |
| SSH | `hostname` prints the VM name | `vm-career-platform` | Pass |
| Files survived | `app`, `.env`, `.venv`, `career_platform.db` present | All present, plus `uv.lock`, `snapshots/`, `migrations/` | Pass |
| App not running | `curl` refused, exit 7 | `Failed to connect to 127.0.0.1 port 8000`, exit 7 | Pass |
| Nothing on 8000 or 80 | Only `:22` and the local DNS helper | `0.0.0.0:22` and `[::]:22` (sshd), `127.0.0.53:53` and `127.0.0.54:53` (systemd-resolved) | Pass |

The disk kept every file; the process that served the site lived in memory and ended when the VM was deallocated.

---

## 2. The service (systemd)

**What this is:** A *service* is a program that should always be running. systemd is the first program Ubuntu starts, and it starts and watches everything else. A *unit file* tells systemd what to run, as which user, from which folder, and what to do if it stops.
- **`enable`** means "start this at every boot".
- **`start`** means "start it now".
- **`Restart=on-failure`** means "if it dies unexpectedly, start it again".

Uvicorn's `--workers 2` gives one main process plus two workers. If one worker crashes, the other keeps answering while the main process replaces it.

- [x] **Service 1: Write the unit file**
  - **Where:** VM
  - **Run:**
    ```bash
    sudo tee /etc/systemd/system/career-platform.service > /dev/null <<'EOF'
    [Unit]
    Description=career-platform (FastAPI on Uvicorn, behind Nginx)
    After=network-online.target
    Wants=network-online.target

    [Service]
    Type=simple
    User=azureuser
    Group=azureuser
    WorkingDirectory=/home/azureuser/career-platform
    ExecStart=/home/azureuser/career-platform/.venv/bin/uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8000 --workers 2
    Restart=on-failure
    RestartSec=3

    [Install]
    WantedBy=multi-user.target
    EOF
    sudo systemd-analyze verify /etc/systemd/system/career-platform.service
    ```
  - **Why:**
    - `User=azureuser` keeps the app off root.
    - `WorkingDirectory` is where the app finds `.env` and the database.
    - `127.0.0.1` keeps Uvicorn reachable only from inside the VM.
    - `--workers 2` handles a single crash.
    - `Restart=` handles the main process dying.
  - **Check:** `systemd-analyze verify` prints nothing (no errors).
  - **Undo:** `sudo rm /etc/systemd/system/career-platform.service && sudo systemctl daemon-reload`

- [x] **Service 2: Load, enable, and start it**
  - **Where:** VM
  - **Run:** `sudo systemctl daemon-reload && sudo systemctl enable --now career-platform`
  - **Why:**
    - `daemon-reload` makes systemd read the new file.
    - `enable` adds it to boot.
    - `--now` also starts it immediately.
  - **Check:** Output includes `Created symlink /etc/systemd/system/multi-user.target.wants/career-platform.service`.
  - **Undo:** `sudo systemctl disable --now career-platform`

- [x] **Service 3: Prove it's the right app, in the right place, as the right user**
  - **Where:** VM
  - **Run:**
    ```bash
    systemctl is-enabled career-platform; systemctl is-active career-platform
    systemctl status career-platform --no-pager | head -12
    ps -ef | grep [u]vicorn
    sudo ss -ltnp | grep ':8000'
    curl -fsS http://127.0.0.1:8000/health; echo
    curl -fsS http://127.0.0.1:8000/ | grep -c "Caelon King"
    ```
  - **Why:**
    - `ps` shows the process tree. The main process's parent (PPID) is `1`, which is systemd, and the two workers' PPID is the main process's PID.
    - The name check proves the app loaded my `.env` and database, not the demo.
  - **Check:**
    - `enabled` and `active`.
    - `ps` shows lines owned by `azureus+`: one main process with PPID 1 and two workers whose PPID is the main process's PID. An extra Python "resource tracker" helper is normal.
    - `ss` shows `127.0.0.1:8000`, **not** `0.0.0.0`.
    - `{"status":"ok"}` and a count ≥ 1.
  - **Undo:** Read-only.

**Results (2026-10-05):**

| Check | Expected | Actual | Result |
|---|---|---|---|
| Unit file didn't exist before | No such file | No such file | Pass |
| `systemd-analyze verify` | No errors | No output, exit 0 | Pass |
| `enable --now` | Boot symlink created | `Created symlink /etc/systemd/system/multi-user.target.wants/career-platform.service` | Pass |
| `is-enabled` / `is-active` | `enabled` / `active` | `enabled` / `active` | Pass |
| Main process | Owned by `azureuser`, PPID 1 (systemd) | PID 1467, `azureus+`, PPID 1, `uvicorn … --workers 2` | Pass |
| Workers | Two, PPID = main process | PIDs 1469 and 1470, PPID 1467 (`multiprocessing.spawn`) | Pass |
| Extra helper | A Python resource tracker is normal | PID 1468, PPID 1467 (`multiprocessing.resource_tracker`) | Pass |
| Listening address | `127.0.0.1:8000`, not `0.0.0.0` | `127.0.0.1:8000`, sockets held by 1467, 1469, 1470 | Pass |
| App health | `{"status":"ok"}` | `{"status":"ok"}` | Pass |
| My data, not the demo | "Caelon King" on the home page | Count 2 (title and heading) | Pass |
| Memory | Fits in 1 GiB | 169.8 MB for main + 2 workers + helper | Pass |

**Finding:** the workers' command line is `python -c "from multiprocessing.spawn import spawn_main…"`, which doesn't contain the word "uvicorn". So `ps -ef | grep uvicorn` shows **only the main process**. To see the whole family, use `ps -ef --forest | grep [c]areer-platform`, or `systemctl status career-platform`, whose CGroup tree lists all four.

---

## 3. The front door (Nginx)

**What this is:** Nginx is a web server built to face the Internet. It deals with slow and malformed requests before they reach Python, and it's where HTTPS goes next session. Here it does one job: listen on port 80 and pass every request to Uvicorn (`proxy_pass`). That pattern is called a *reverse proxy*.
- **`sites-available`** holds every site Nginx knows about.
- **`sites-enabled`** holds links to the ones it actually serves.
- **`nginx -t`** checks the config before a reload, so a typo can't take the site down.

Nginx's main process runs as root, because only root can open ports below 1024. Its workers run as `www-data`.

- [x] **Front door 1: Install Nginx**
  - **Where:** VM
  - **Run:** `sudo apt-get update -q && sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -q nginx`
  - **Why:** It isn't installed yet; Tuesday only added git and sqlite3.
  - **Check:** `nginx -v` prints a version, and `systemctl is-enabled nginx` → `enabled`, since the package enables it at boot.
  - **Undo:** `sudo apt-get purge -y nginx nginx-common && sudo apt-get autoremove -y`

- [x] **Front door 2: Write the site file**
  - **Where:** VM
  - **Run:**
    ```bash
    sudo tee /etc/nginx/sites-available/career-platform > /dev/null <<'EOF'
    server {
        listen 80 default_server;
        listen [::]:80 default_server;
        server_name _;

        client_max_body_size 1m;

        location / {
            proxy_pass http://127.0.0.1:8000;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
    }
    EOF
    ```
  - **Why:**
    - `default_server` with `server_name _` answers for the IP and for my domain later, with no change.
    - The headers tell the app the original host and visitor address.
  - **Check:** `sudo cat /etc/nginx/sites-available/career-platform` shows the file.
  - **Undo:** `sudo rm /etc/nginx/sites-available/career-platform`

- [x] **Front door 3: Enable mine, disable the welcome page, test, reload**
  - **Where:** VM
  - **Run:**
    ```bash
    sudo ln -s /etc/nginx/sites-available/career-platform /etc/nginx/sites-enabled/career-platform
    sudo rm /etc/nginx/sites-enabled/default
    sudo nginx -t && sudo systemctl reload nginx
    ```
  - **Why:** Only one site should answer port 80. `nginx -t` blocks a bad config from going live.
  - **Check:** `nginx -t` says `syntax is ok` and `test is successful`.
  - **Undo:**
    ```bash
    sudo rm /etc/nginx/sites-enabled/career-platform
    sudo ln -s /etc/nginx/sites-available/default /etc/nginx/sites-enabled/default
    sudo nginx -t && sudo systemctl reload nginx
    ```

- [x] **Front door 4: Prove Nginx answers with my site**
  - **Where:** VM
  - **Run:**
    ```bash
    ls /etc/nginx/sites-enabled
    curl -sI http://localhost | head -5
    curl -s http://localhost/ | grep -c "Caelon King"
    sudo ss -ltnp | grep -E ':(80|8000) '
    ps -o user,pid,ppid,cmd -C nginx
    ```
  - **Why:**
    - The `Server:` header shows Nginx answered the visitor, but Uvicorn built the page behind it.
    - `ss` shows who faces outward and who doesn't.
  - **Check:**
    - only `career-platform` is enabled
    - `HTTP/1.1 200 OK` with `Server: nginx/...`
    - a count ≥ 1
    - `0.0.0.0:80` (and `[::]:80`) owned by nginx
    - `127.0.0.1:8000` owned by uvicorn
    - one nginx process as `root` and workers as `www-data`
  - **Undo:** Read-only.

**Results (2026-10-05):**

| Check | Expected | Actual | Result |
|---|---|---|---|
| Install | Nginx installed, enabled at boot | `nginx/1.24.0 (Ubuntu)`, `enabled`, `active` | Pass |
| Site file didn't exist before | No such file | No such file | Pass |
| `nginx -t` | Syntax ok, test successful | `syntax is ok`, `test is successful`; reloaded | Pass |
| Enabled sites | Only `career-platform` | `career-platform` (default link removed) | Pass |
| `curl -sI http://localhost` (HEAD) | `200`, `Server: nginx` | **`405 Method Not Allowed`**, `Server: nginx/1.24.0`, `Content-Type: application/json` | See finding |
| GET headers via Nginx | `200`, `Server: nginx` | `HTTP/1.1 200 OK`, `Server: nginx/1.24.0 (Ubuntu)`, `text/html`, 4609 bytes | Pass |
| My data through Nginx | "Caelon King" on the page; no welcome page | Name count 2; "Welcome to nginx" count 0 | Pass |
| Who listens where | Nginx on `0.0.0.0:80` and `[::]:80`; Uvicorn on `127.0.0.1:8000` | Exactly that | Pass |
| Nginx process users | Master as root, workers as `www-data` | PID 2109 `root` (PPID 1); PIDs 2239 and 2240 `www-data` (PPID 2109) | Pass |
| Uvicorn received the proxied requests | GET lines in the app log | `"GET / HTTP/1.0" 200 OK` x2 | Pass |

**Finding (ruling):** `curl -I` sends a `HEAD` request, and the app's routes are `@router.get(...)` only (`app/routes/public.py:47`), so FastAPI answers `405`. Sending HEAD straight to Uvicorn gives the same `405` with `server: uvicorn`, so it's the app, not Nginx. The site itself is fine, because browsers use GET. To see the headers of a real page load, use `curl -s -D - -o /dev/null http://localhost/`. I didn't change the code, since this plan doesn't change repo files. Making `/` also answer HEAD would be a small separate fix.

**Both programs answered:** the `Server: nginx` header comes from Nginx, the front door. The body, and the `405` with its JSON content type, came from Uvicorn behind it.

---

## 4. Open port 80 (my step, in the portal)

**What this is:** Nginx is listening, but Azure's firewall (the NSG) still drops everything except SSH. Port 80 opens to everyone because Nginx is built for that. Port 8000 stays closed, so nobody can skip the front door.

- [x] **Firewall 1: Confirm it's blocked first**
  - **Where:** Laptop
  - **Run:** `curl -s -m 8 -o /dev/null -w "%{http_code}\n" http://52.162.50.66/`
  - **Why:** Shows a firewall drop looks like a hang or timeout, not an error page.
  - **Check:** prints `000` after about 8 seconds.
  - **Undo:** Read-only.

- [x] **Firewall 2: Add the rule (me)**
  - **Where:** Portal: VM → Networking → Network settings → Add inbound port rule
  - **Run:** Source **Any**, destination port **80**, protocol **TCP**, action Allow, priority **320**, name **`Allow-HTTP-80`**.
  - **Why:** Lets visitors reach Nginx.
  - **Check:** The rule list shows `Allow-SSH-Laptop` (300) and `Allow-HTTP-80` (320), and nothing for 8000.
  - **Undo:** Delete `Allow-HTTP-80` in the portal.

- [x] **Firewall 3: My site at the public IP, and 8000 still closed**
  - **Where:** Laptop, browser, and phone
  - **Run:**
    ```bash
    curl -s http://52.162.50.66/ | grep -c "Caelon King"
    curl -s -m 8 -o /dev/null -w "%{http_code}\n" http://52.162.50.66:8000/
    ```
    Then open `http://52.162.50.66` in a browser, and on my phone with Wi-Fi off.
  - **Why:** Proves the whole path from the Internet to my data, and that the back door is shut.
  - **Check:** a count ≥ 1; `000` for port 8000; the browser and phone show my name with no port in the address.
  - **Undo:** Read-only.

**Results (2026-10-05):**

| Check | Expected | Actual | Result |
|---|---|---|---|
| Before the rule: `http://52.162.50.66/` | Hangs, then `000` | `000` after 8 s, curl exit 28 (timeout) | Pass |
| Before the rule: `:8000` | Hangs, then `000` | `000` after 8 s, curl exit 28 (timeout) | Pass |
| NSG before | Only the SSH rule | `Allow-SSH-Laptop` (300, port 22) | Pass |
| Rule added (me, in the portal) | `Allow-HTTP-80`: 320, TCP 80 from Any | `Allow-HTTP-80`: 320, TCP, port 80, source `*`, Allow, Inbound | Pass |
| NSG after | SSH from my laptop's `/32`, 80 from anyone, nothing for 8000 | `Allow-SSH-Laptop` (300, 22, my laptop's `/32`) and `Allow-HTTP-80` (320, 80, `*`) | Pass |
| After the rule: `http://52.162.50.66/` from the laptop | `200` with my name | `200`, "Caelon King" count 2, `Server: nginx/1.24.0 (Ubuntu)` | Pass |
| After the rule: `:8000` from the laptop | Still times out | `000` after 8 s, curl exit 28 | Pass |
| Browser and phone with Wi-Fi off | My site, no port in the address | Site loaded in my laptop browser and on my phone (cellular) | Pass |
| Browser at `:8000` | Hangs | Hung | Pass |

Nginx was already listening on port 80 on the VM, but Azure's firewall dropped the request before it got there. A drop looks like silence, not an error page.

---

## 5. Restart and crash evidence (I run the tests)

**What this is:** The test Tuesday's setup failed. I restart the VM from the portal and kill processes on purpose. The agent only gathers the evidence and writes it here.

- [x] **Restart 1: Portal Restart (me), then evidence**
  - **Where:** Portal (me), then VM
  - **Run:** Portal → Restart (not Stop). Wait for Running. Then:
    ```bash
    uptime -s
    systemctl show career-platform -p ActiveEnterTimestamp
    systemctl show nginx -p ActiveEnterTimestamp
    curl -sI http://localhost | grep -i '^server'
    curl -s http://localhost/ | grep -c "Caelon King"
    ```
  - **Why:** If the service started within seconds of boot, systemd started it, because nobody logged in to do it.
  - **Check:** Both `ActiveEnterTimestamp` values are within about a minute of `uptime -s`; `Server: nginx`; a count ≥ 1.
  - **Undo:** None needed.

- [x] **Restart 2: Kill one worker (me asking, agent runs)**
  - **Where:** VM
  - **Check:** The killed worker's PID is replaced by a new one; the main process's PID is unchanged; `systemctl status` stays `active` the whole time. Uvicorn recovered it, not systemd.

- [x] **Restart 3: Kill the main process with `kill -9`**
  - **Where:** VM
  - **Check:** Every Uvicorn PID changes; `systemctl status` five seconds apart shows a new main PID and a recent "Active: active (running) since" time. systemd restarted it because of `Restart=on-failure`.

- [x] **Restart 4: Stop the service, see the 502, start it again**
  - **Where:** VM
  - **Run:** `sudo systemctl stop career-platform`, `curl -sI http://localhost | head -1`, `sudo tail -n 3 /var/log/nginx/error.log`, then `sudo systemctl start career-platform`.
  - **Check:**
    - `HTTP/1.1 502 Bad Gateway` comes from Nginx.
    - The error log shows `connect() failed (111: Connection refused) while connecting to upstream`.
    - After the start, `curl` returns `200` again.
    - A deliberate `systemctl stop` is **not** restarted, because `Restart=` only covers unexpected exits.

**Results (2026-10-05):**

**Restart 1: portal Restart**

| Check | Expected | Actual | Result |
|---|---|---|---|
| Boot time (`uptime -s`) | — | `2026-10-06 01:19:44` UTC | — |
| `career-platform` started | Within about a minute of boot | `01:19:53` UTC (9 s after boot) | Pass |
| `nginx` started | Within about a minute of boot | `01:19:54` UTC (10 s after boot) | Pass |
| Service restarts or failures | None | `NRestarts=0`, `Result=success` | Pass |
| Through Nginx, on the VM | `200`, `Server: nginx`, my name | `HTTP/1.1 200 OK`, `Server: nginx/1.24.0`, "Caelon King" count 2 | Pass |
| From the laptop | `200` | `200` | Pass |

Nobody logged in before the service started. The start times come from systemd, 9–10 seconds after boot.

**Finding: a 502 right after the restart.** My first browser reload, as soon as the portal said Running, got `502 Bad Gateway`. The journal (seconds since boot) explains it:

| ~s after boot | Event |
|---|---|
| 9.0 | systemd starts `career-platform` |
| ~10 | My request reaches Nginx; Nginx logs `connect() failed (111: Connection refused) while connecting to upstream`, so the browser gets a 502 |
| 10.4 | Uvicorn starts listening on `127.0.0.1:8000` |
| 13.3 | Both workers finish starting (`Application startup complete`) |

The portal shows Running as soon as Ubuntu boots, but the app needs about 4 more seconds to load Python and start its workers. The setup was fine: a reload a few seconds later returned `200`, with no restarts. The 502 came from Nginx (up) with nothing answering behind it yet, which is the same layer the section's stop test shows on purpose.

**Restart 2: `kill -9` one worker**

| | Main | Resource tracker | Worker A | Worker B |
|---|---|---|---|---|
| Before | 667 (PPID 1) | 871 | **873** | 876 |
| After `kill -9 873` | 667 (PPID 1) | 871 | — (dead) | 876 |
| New | | | **1346** (PPID 667, age 3 s) | |

| Check | Expected | Actual | Result |
|---|---|---|---|
| Killed worker gone | PID 873 no longer exists | Gone | Pass |
| Replacement worker | New PID, parent = main | 1346, PPID 667 | Pass |
| Main process unchanged | Same PID | 667 before and after | Pass |
| systemd didn't act | Same start time, no restarts | `active (running) since 01:19:53`, `NRestarts=0` | Pass |
| Uvicorn's log | It noticed and replaced the worker | `Child process [873] died` → `Started server process [1346]` → `Application startup complete` | Pass |
| Site | Still `200` | `200` | Pass |

The other worker (876) kept serving the whole time. Uvicorn's main process, not systemd, replaced the dead worker.

**Restart 3: `kill -9` the main process**

| | Main | Resource tracker | Workers |
|---|---|---|---|
| Before | **667** (PPID 1) | 871 | 876, 1346 |
| After | **1550** (PPID 1) | 1551 | 1552, 1553 |

| Time (UTC) | Event (from `journalctl`) |
|---|---|
| 01:23:40.000 | `Main process exited, code=killed, status=9/KILL` |
| 01:23:40.02–.14 | Workers 876 and 1346 log `Shutting down` → `Finished server process` (their parent was gone) |
| 01:23:40.150 | `Failed with result 'signal'` |
| 01:23:43.262 | `Scheduled restart job, restart counter is at 1` (3 s later, `RestartSec=3`) |
| 01:23:43.266 | `Started career-platform.service` |
| 01:23:44.27 | New workers 1552 and 1553: `Application startup complete` |

| Check | Expected | Actual | Result |
|---|---|---|---|
| Status #1 (immediately) | Service is down | `deactivating (stop-sigterm) (Result: signal)`, `Main PID: 667 (code=killed, signal=KILL)` | Pass |
| Status #2 (5 s later) | systemd restarted it | `active (running) since 01:23:43`, `Main PID: 1550` | Pass |
| Every PID changed | Yes | 667/871/876/1346 → 1550/1551/1552/1553 | Pass |
| Restart counter | 1 | `NRestarts: 1` | Pass |
| Site | `200` | `200` | Pass |

Downtime was about 4 seconds: 3 s of `RestartSec` plus about 1 s of startup. Uvicorn's main process recovers from a worker crash; systemd recovers from a crash of Uvicorn itself.

**Agent mistake, no impact:** the first attempt found the "main PID" with `ps -C uvicorn --ppid 1`. `ps` combines those two filters with OR, so it picked PID 137 (`systemd-journald`). The `kill -9` failed with `Operation not permitted`, because `azureuser` can't signal root's processes, and nothing changed (`NRestarts=0`, same PID 667, site `200`). The retry used `pgrep -u azureuser -P 1 -f "bin/uvicorn app.main:create_app"`, checked there was exactly one match (667), and only then killed it. This also shows why the app doesn't run as root: as root, that typo would have killed the logging service.

**Restart 4: `systemctl stop`, then the 502**

| Check | Expected | Actual | Result |
|---|---|---|---|
| After `sudo systemctl stop career-platform` (01:25:25) | App down, Nginx up | `career-platform: inactive`, `nginx: active`, 0 listeners on `:8000` | Pass |
| `GET http://localhost/` | `502` from Nginx | `HTTP/1.1 502 Bad Gateway`, `Server: nginx/1.24.0 (Ubuntu)`, Nginx's own HTML page `<h1>502 Bad Gateway</h1>` | Pass |
| Nginx error log | Upstream refused | `connect() failed (111: Connection refused) while connecting to upstream, client: ::1, … upstream: "http://127.0.0.1:8000/", host: "localhost"` | Pass |
| A deliberate stop isn't restarted | Still `inactive` 5 s later | `inactive`, `NRestarts: 1` (unchanged since Restart 3) | Pass |
| Browser shows the 502 (me) | Nginx's 502 page | White "502 Bad Gateway" page with "nginx/1.24.0 (Ubuntu)" under it | Pass |
| `sudo systemctl start career-platform` | `active`, still enabled, site `200` | `active`, `enabled`, started 01:28:48 UTC, new main PID 1791; `200` through Nginx with "Caelon King" (count 2); `200` from the laptop | Pass |
| Ports after start | `0.0.0.0:80`, `[::]:80`, `127.0.0.1:8000` | Exactly those | Pass |

**Three failures, three layers:**

| What you see | Who's talking | What it means |
|---|---|---|
| The page hangs, then times out | Nobody (Firewall 1, `:8000` checks) | The NSG dropped the request before it reached the VM |
| `502 Bad Gateway` (Restart 1 finding, Restart 4) | Nginx | Nginx is up; the app behind it isn't answering |
| `405` on `HEAD /` (Front door finding) | The app | The app is up and answering, but it doesn't accept that method |

`Restart=on-failure` restarts the app after a crash (Restart 3), but not after someone stops it on purpose with `systemctl stop`.

---

## 6. Domain (my step, in Cloudflare and Namecheap)

**What this is:** Namecheap is the *registrar*: it records that I own the name and tells the `.com` servers who answers for it. Cloudflare is the *DNS host*: its name servers hold my A records (`@` and `www` → `52.162.50.66`, set to DNS only, the gray cloud). Nothing on the VM changes, because Nginx's `server_name _` answers for any name.

- [ ] **Domain 1: Check the switch and the address**
  - **Where:** Laptop
  - **Run:** `nslookup -type=NS <my-domain>`, then `nslookup <my-domain>`, or `nslookup <my-domain> 1.1.1.1` if my network is caching an old answer.
  - **Check:** The NS records are `*.ns.cloudflare.com`, and the address is `52.162.50.66`, not `104.x` or `172.x`, which would mean the proxy is on. `http://<my-domain>` shows my site; on campus Wi-Fi, use a phone with Wi-Fi off.
  - **Undo:** In Namecheap, set Nameservers back to Namecheap BasicDNS.

**Results (2026-10-05, about 01:50 UTC; in progress):**

Domain: `caelonk.me`, registered 2026-10-05 at Namecheap. Cloudflare Free plan, DNS only. Name servers changed in Namecheap at 01:43 UTC.

| Check | Expected | Actual | Result |
|---|---|---|---|
| Registry record (RDAP) | Cloudflare name servers | `naomi.ns.cloudflare.com`, `damiete.ns.cloudflare.com`; "last changed" 2026-10-06 01:43 UTC | Pass |
| `.me` TLD server (`a0.nic.me`) | Cloudflare name servers | Still `dns1/dns2.registrar-servers.com` (Namecheap); the registry hadn't published the change yet | Waiting |
| `nslookup -type=NS caelonk.me 1.1.1.1` and the default resolver | `*.ns.cloudflare.com` | Still Namecheap's | Waiting |
| Cloudflare's own servers (`nslookup caelonk.me naomi.ns.cloudflare.com`, same for `damiete`) | `52.162.50.66` for `@` and `www` | `52.162.50.66` for both names, on both servers | Pass |
| Old answer still cached | — | `185.199.108–111.153` (GitHub Pages addresses that Namecheap had configured), `www` as an alias | Expected until the switch |
| Nginx answers for the name, from inside the VM | `200`, my name | `caelonk.me` and `www.caelonk.me`: `200`, `Server: nginx`, "Caelon King" count 2 | Pass |
| From my laptop on campus Wi-Fi | — | `503` "Web Page Blocked" from LMU's web filter; the request never reached the VM (no line in the app log) | Expected on campus |
| `http://caelonk.me` in a browser, off campus or on a phone with Wi-Fi off | My site | _Pending: after the `.me` servers publish the change_ | |

**Still to do:** when Cloudflare emails that the domain is active, run `nslookup -type=NS caelonk.me 1.1.1.1` (expect `*.ns.cloudflare.com`) and `nslookup caelonk.me 1.1.1.1` (expect `52.162.50.66`), then open `http://caelonk.me` on a phone with Wi-Fi off. The VM must be running for the browser check, and the site starts on its own at boot.

---

## 7. Record

**What this is:** The network setup written down, not just working. The agent fills this in at the end.

- [x] **Record 1: Listening ports** from `sudo ss -ltnp`, as a table of address:port, the program, and why. Expect `0.0.0.0:22` sshd, `0.0.0.0:80` nginx, `127.0.0.1:8000` uvicorn, `127.0.0.53:53` systemd-resolved, plus IPv6 lines.
- [x] **Record 2: Addresses.** Private IP from `ip -4 addr show eth0` (`10.0.0.4`) and public IP `52.162.50.66`, with why the public IP never appears on the VM: Azure holds it and forwards traffic to the private one.
- [x] **Record 3: NSG inbound rules** and why each exists. The SSH rule's source is written as "my laptop's `/32`", never the address.
- [x] **Record 4: Public-safety check** before commit: `grep` this file for my laptop IP, subscription ID, tenant ID, and emails. Expect no matches.

**Results (2026-10-05, about 01:55 UTC):**

### Listening ports (`sudo ss -ltnp`)

| Address:port | Program | Who can reach it | Why it's there |
|---|---|---|---|
| `0.0.0.0:22` and `[::]:22` | `sshd` | My laptop only (NSG `Allow-SSH-Laptop`) | Admin access with my SSH key |
| `0.0.0.0:80` and `[::]:80` | `nginx`: master PID 764 (root), workers 766 and 767 (`www-data`) | Anyone (NSG `Allow-HTTP-80`) | The front door; reverse proxy to Uvicorn |
| `127.0.0.1:8000` | `uvicorn`: main PID 1791, workers 1796 and 1797 (shown as `python`) | Only programs on the VM. Loopback isn't reachable from the network, and the NSG has no 8000 rule | The app, run by systemd as `azureuser` with 2 workers |
| `127.0.0.53:53` and `127.0.0.54:53` | `systemd-resolved` | Only programs on the VM | Ubuntu's local DNS helper, which looks up names for programs on the VM |

`0.0.0.0` means "every address this machine has", so Nginx and sshd accept connections arriving on `eth0`. `127.0.0.1` means "only from this machine", which is why Uvicorn can't be reached around Nginx even if a firewall rule were wrong.

### Addresses

| Address | Value | Where it lives |
|---|---|---|
| Private IP | `10.0.0.4/24` on `eth0` (`ip -4 addr`, `hostname -I`) | On the VM, inside Azure's virtual network `10.0.0.0/16` |
| Public IP | `52.162.50.66` (Static, Standard SKU) | **Not on the VM.** `ip addr` contains it 0 times. Azure holds it on its network edge and forwards traffic to `10.0.0.4` (1:1 NAT). The VM only ever sees its private address |
| Loopback | `127.0.0.1/8` on `lo` | The VM talking to itself; Nginx reaches Uvicorn here |

Because the public IP is static, it survives deallocation, so the `caelonk.me` A records keep working while the VM is off.

### NSG inbound rules (`vm-career-platformNSG`, on the VM's network interface)

| Priority | Name | Port / protocol | Source | Action | Why it exists |
|---|---|---|---|---|---|
| 300 | `Allow-SSH-Laptop` | 22 / TCP | My laptop's public `/32` | Allow | So I can administer the VM over SSH, and nobody else can try |
| 320 | `Allow-HTTP-80` | 80 / TCP | Any | Allow | So visitors can reach Nginx. This one is meant to be public |
| 65000 | `AllowVnetInBound` (Azure default) | Any | `VirtualNetwork` | Allow | Lets resources inside the same virtual network talk to each other |
| 65001 | `AllowAzureLoadBalancerInBound` (Azure default) | Any | `AzureLoadBalancer` | Allow | Lets Azure's health probes reach the VM |
| 65500 | `DenyAllInBound` (Azure default) | Any | Any | **Deny** | Drops everything else, including port 8000 |

Tuesday's temporary port-8000 rule no longer exists. A request to `:8000` from the Internet falls through to `DenyAllInBound`, which is why it hangs instead of being refused.

### Public-safety check

Scanned this file for my laptop's IP, the subscription and tenant IDs, my email addresses, the admin password, my Windows username, SSH key and host-key fingerprints, and my phone number: **no matches**. A pattern scan for emails found none. The only IPv4 addresses are `52.162.50.66` (the VM's public IP, meant to be shared), `10.0.0.4` and `10.0.0.0` (private), `127.0.0.1/53/54` (loopback), `0.0.0.0`, `1.1.1.1` (Cloudflare's resolver), and the `185.199.x.153` GitHub Pages addresses from the old DNS answer. My laptop's address appears in Nginx's error log and Uvicorn's access log on the VM, but it was never copied here.

---

## 8. Shutdown

- [ ] **Shutdown 1: Deallocate (me, in the portal)**
  - **Where:** Portal
  - **Run:** Stop, then wait for "Stopped (deallocated)". Keep `Allow-HTTP-80` for next session.
  - **Check:** `az vm show -d -g rg-career-platform -n vm-career-platform --query powerState -o tsv` → `VM deallocated`. The A records still point at the static IP, and the site comes back on its own at the next start.
  - **Undo:** Start the VM.

**Results:**

---

## Troubleshooting

| What I see | What it means | Look at first |
|---|---|---|
| Nginx "Welcome to nginx" page | The default site is still enabled | `ls /etc/nginx/sites-enabled` |
| `502 Bad Gateway` | Nginx is up, the app behind it isn't | `systemctl status career-platform`, `journalctl -u career-platform -n 50` |
| Unit fails: "No such file or directory" | A path in the unit file is wrong | `WorkingDirectory=` and the `.venv/bin/uvicorn` path |
| Unit fails: "Address already in use" | Something else holds port 8000, like a hand-started Uvicorn | `sudo ss -ltnp \| grep 8000` |
| Demo profile or snapshot instead of my data | The app started in the wrong folder and missed `.env` | `WorkingDirectory=`, `DATABASE_URL` in `.env` |
| `nginx -t` error | A typo in the site file | The file and line number in the message |
| `http://52.162.50.66` hangs | The NSG has no port 80 rule, or the VM is off | Portal inbound rules, VM status |
| Site gone after Restart | The service was started but not enabled | `systemctl is-enabled career-platform` |
| SSH hangs | My laptop's IP changed, or the VM is off | `Allow-SSH-Laptop` source, VM status |

Never fix a problem by opening port 8000, running the app as root, or allowing SSH from Any.

## Self-review

- **Spec coverage:**
  - no port → sections 3 and 4
  - starts at boot → `enable` in Service 2, proved in Restart 1
  - comes back after a crash → `Restart=on-failure`, proved in Restart 3
  - one crash doesn't take the site down → `--workers 2`, proved in Restart 2
  - 8000 closed → Global Constraints, Firewall 3
  - not root → `User=azureuser`, Service 3
  - service name → Service 1
  - uses the existing folder → `WorkingDirectory`, Service 3
  - portal steps are mine → Preflight 1, Firewall 2, Restart 1, Domain, Shutdown
- **Placeholders:** `<my-domain>` is filled in when I run Domain 1. Every Results block is filled during execution.
- **Undo:** every section that changes something has an undo step.
