# Midterm request path: caelonk.me

What happens when I enter `caelonk.me` in a browser and press Enter. Drawn for Railway, where the site runs now, with what changes on Azure at the end.

Assumptions: no cached DNS answer, a new HTTPS connection over TCP, and the browser tries `http` first.

Anything marked "unverified" isn't backed by evidence in this repo. That covers the whole campus side, because the Exercise 01 network observations aren't stored here.

## 1. Hardware and services (where things are)

```mermaid
flowchart LR
  subgraph Campus["Palm South / LMU network (campus details unverified)"]
    L["Laptop Wi-Fi interface<br/>private IP from DHCP"]
    AP["Access point"]
    SW["Campus switch"]
    R["Campus router<br/>= default gateway"]
    FW["LMU firewall + NAT<br/>private → public IP"]
    DHCP[("DHCP server")]
    RES[("DNS resolver")]
  end

  ISP["LMU's upstream ISP<br/>(unknown)"]
  NET["Internet routers<br/>(several hops)"]
  CF[("Cloudflare authoritative DNS<br/>caelonk.me CNAME → l29it1kr.up.railway.app<br/>DNS only, flattened to A records")]

  subgraph RW["Railway"]
    EDGE["Railway edge<br/>TLS ENDS HERE<br/>Let's Encrypt cert for caelonk.me"]
    APP["App container<br/>Uvicorn on $PORT<br/>--proxy-headers"]
    PG[("PostgreSQL<br/>via DATABASE_URL")]
  end

  L -- Wi-Fi --- AP --- SW --- R --- FW --- ISP --- NET
  NET -- "TCP 443, HTTPS<br/>client: browser · server: edge" --- EDGE
  EDGE -- "plain HTTP + X-Forwarded-Proto<br/>client: edge · server: app" --> APP
  APP -- "SQL<br/>client: app · server: Postgres" --> PG

  DHCP -. "IP, subnet, gateway, DNS server" .-> L
  L -. "DNS query, UDP 53<br/>(separate exchange)" .-> RES
  RES -. "recursive lookup" .-> CF
```

## 2. Order of events (when things happen)

```mermaid
sequenceDiagram
  autonumber
  participant B as Browser (laptop)
  participant RES as DNS resolver
  participant CF as Cloudflare DNS
  participant E as Railway edge
  participant A as App (Uvicorn)
  participant P as PostgreSQL

  Note over B: Assume no cached DNS answer and a new connection.<br/>Browser reads "caelonk.me", tries http first
  B->>RES: Where is caelonk.me? (UDP 53)
  RES->>CF: Ask the authoritative server
  CF-->>RES: A records for Railway's edge (flattened CNAME)
  RES-->>B: Railway edge IP
  B->>E: TCP 80, GET http://caelonk.me/
  E-->>B: 301 → https://caelonk.me/
  B->>E: TCP 443, TLS handshake
  Note over B,E: Browser checks the certificate's name, dates and chain
  B->>E: GET / (encrypted)
  Note over E: TLS ends here
  E->>A: GET / over plain HTTP, X-Forwarded-Proto: https
  A->>P: Query projects
  P-->>A: Rows
  A-->>E: 200 HTML
  E-->>B: 200 HTML (encrypted)
  Note over B: Browser renders the HTML
  B->>E: Separate requests for site.css, fonts, favicon
```

## 3. What changes on Azure

| Part | Railway (above) | Azure VM |
|---|---|---|
| DNS answer | Flattened CNAME → Railway edge | `A @ 52.162.50.66`, DNS only |
| First thing the traffic hits | Railway edge | NSG (`vm-career-platformNSG`): 80 and 443 open to anyone, 22 only from my laptop |
| Where TLS ends | Railway edge | Nginx on port 443 on the VM (`10.0.0.4`) |
| Who owns the certificate | Railway issues and renews it | Certbot on the VM, renewed by `certbot.timer` |
| Path to the app | Edge → container on `$PORT` | Nginx → `127.0.0.1:8000` over loopback |
| Database | PostgreSQL service | SQLite file on the VM's disk |

## Sources in this repo

- DNS records: `docs/evidence/dns-after-zoho.md`
- Railway edge, redirect and domain setup: `docs/superpowers/plans/2026-10-08-railway-postgres-migration.md`
- Proxy headers and `$PORT`: `Dockerfile`
- Azure NSG, Nginx and where TLS ended: `docs/how-this-site-is-secured.md`
