# Azure VM check, 2026-10-21

The VM had been deallocated since 2026-10-13. It was started again on 2026-10-21 so it
keeps running as Project 1 requires, and booted at **04:15:35 UTC**. These checks ran
between 04:18 and 04:20 UTC and changed nothing. Public DNS no longer points at the VM,
so the HTTPS check sends the request to its IP while keeping the name `caelonk.me`.

## Service management after the boot

`uptime -s`, `systemctl is-enabled`, `systemctl is-active`, `systemctl show … ActiveEnterTimestamp NRestarts`, over SSH:

| Unit | Enabled | Active | Started (UTC) |
|---|---|---|---|
| `career-platform` | enabled | active | 04:15:44, 9 s after boot, `NRestarts=0` |
| `nginx` | enabled | active | 04:15:45, 10 s after boot |
| `certbot.timer` | enabled | active | |

Nobody logged in before these started. The unit is the one in
[`deploy/systemd/career-platform.service`](../../deploy/systemd/career-platform.service):
`User=azureuser`, `--host 127.0.0.1 --port 8000 --workers 2`, `Restart=on-failure`.

## What listens where (`sudo ss -ltnp`)

| Address:port | Program |
|---|---|
| `0.0.0.0:22`, `[::]:22` | `sshd` |
| `0.0.0.0:80`, `[::]:80` | `nginx` |
| `0.0.0.0:443`, `[::]:443` | `nginx` |
| `127.0.0.1:8000` | `uvicorn` main process and 2 workers (shown as `python`) |
| `127.0.0.53:53`, `127.0.0.54:53` | `systemd-resolved` |

## Network rules (`az network nsg rule list`, `vm-career-platformNSG`)

| Priority | Name | Port | Source |
|---|---|---|---|
| 300 | `Allow-SSH-Laptop` | 22 | One `/32` address, my laptop (checked to be a single `/32` without printing it) |
| 320 | `Allow-HTTP-80` | 80 | Any |
| 330 | `Allow-HTTPS-443` | 443 | Any |

Everything else, including port 8000, falls to Azure's `DenyAllInBound`. VM size
`Standard_B2ats_v2`, public IP `52.162.50.66`.

## App, database and certificate on the VM

| Check | Result |
|---|---|
| `curl http://127.0.0.1:8000/health` | `200` |
| `curl http://127.0.0.1:8000/` | My name appears 5 times |
| SQLite `projects` | 4 rows, all `published` (the same four slugs as on Railway) |
| Code checked out | `4168e95` (the commit before `626e18c`, which only added a document) |
| Certificate file | `CN = caelonk.me`, Let's Encrypt `YE1`, 2026-10-06 to 2027-01-04 |
| Nginx site file | Copied to [`deploy/nginx/career-platform.conf`](../../deploy/nginx/career-platform.conf) |

## Source and target pages compared

Each page was fetched from the VM (`curl --resolve caelonk.me:443:52.162.50.66
https://caelonk.me/…`) and from Railway (`https://caelonk.me/…`) at 04:19 UTC. The text
inside `<main>` was extracted (scripts and styles skipped) and compared with `diff`.

| Page | VM | Railway | Text inside `<main>` |
|---|---|---|---|
| `/` | 200 | 200 | Identical (37 lines) |
| `/projects/technician-dispatch-dashboard` | 200 | 200 | Identical (15 lines) |
| `/projects/third-party-vendor-risk-dashboard` | 200 | 200 | Identical (13 lines) |
| `/projects/gdpr-ccpa-privacy-compliance-assessment` | 200 | 200 | Identical (13 lines) |
| `/projects/legal-document-analyzer` | 200 | 200 | Identical (11 lines) |

So the pages built from the VM's SQLite file and from Railway's PostgreSQL show the same
profile and project content. The two sites run different code versions: Railway has the
GA4 tag and Privacy link, which sit outside `<main>`.

## Still to watch

- The VM's certificate renews through `certbot.timer` only while the VM is running and
  `caelonk.me` resolves to it. DNS now points at Railway, so a renewal attempt before
  2027-01-04 would fail its HTTP check. That only matters if the VM becomes the live
  site again; the rollback in the README covers it.
- Auto-shutdown is `Disabled` (`az resource show` on the schedule, 2026-10-21), so the VM
  runs and bills compute until someone stops it.
