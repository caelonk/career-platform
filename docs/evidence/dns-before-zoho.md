# DNS records for `caelonk.me` before the Zoho Mail setup

Snapshot taken **2026-10-13 21:12 UTC**, before any record was changed for Zoho.
It is the reference for what to put back if the mail change has to be undone.

- **Source:** Cloudflare, the authoritative DNS host for the zone, read through
  the Cloudflare CLI (`cf` 1.0.0-beta.13, logged in as the Owner).
- **Scope:** every record in the zone. The list returned 9 records with a page
  size of 100, so nothing was cut off by paging.
- **Nothing was changed.** Both commands below only read.

```text
cf dns records list -z caelonk.me --per-page 100 --order type
cf dns records export -z caelonk.me
```

## 1. Records

A TTL of `1` is how Cloudflare writes "Auto".

| # | Type | Name | Content | Priority | Proxy | TTL | Created (UTC) | Modified (UTC) | Record ID |
|---|---|---|---|---|---|---|---|---|---|
| 1 | A | `www.caelonk.me` | `192.0.2.1` | | Proxied | Auto | 2026-10-06 01:38 | 2026-10-13 21:09 | `de02731044ebf21564d2e597c258e4bb` |
| 2 | CNAME | `caelonk.me` | `l29it1kr.up.railway.app` | | DNS only | Auto | 2026-10-08 22:18 | 2026-10-08 22:18 | `54c95a56c5bbe19571e74a9bad3a5569` |
| 3 | MX | `caelonk.me` | `eforward1.registrar-servers.com` | 10 | DNS only | Auto | 2026-10-06 01:34 | 2026-10-06 01:34 | `de2a6b941fa7d98921cbc2d8048a6497` |
| 4 | MX | `caelonk.me` | `eforward2.registrar-servers.com` | 10 | DNS only | Auto | 2026-10-06 01:34 | 2026-10-06 01:34 | `9c2b3cd9d611489723e3527e6cf13bb0` |
| 5 | MX | `caelonk.me` | `eforward3.registrar-servers.com` | 10 | DNS only | Auto | 2026-10-06 01:34 | 2026-10-06 01:34 | `37e27c6e2079400525e5a775e3e71a03` |
| 6 | MX | `caelonk.me` | `eforward4.registrar-servers.com` | 15 | DNS only | Auto | 2026-10-06 01:34 | 2026-10-06 01:34 | `a1acffe8cf748b2c08557ced90234aeb` |
| 7 | MX | `caelonk.me` | `eforward5.registrar-servers.com` | 20 | DNS only | Auto | 2026-10-06 01:34 | 2026-10-06 01:34 | `f9e4017da0237d5805e984f49e88533a` |
| 8 | TXT | `caelonk.me` | `"v=spf1 include:spf.efwd.registrar-servers.com ~all"` | | DNS only | Auto | 2026-10-06 01:34 | 2026-10-06 01:34 | `2580d0e19ae2fd04150aa4a83c28a08d` |
| 9 | TXT | `_railway-verify.caelonk.me` | `"railway-verify=ce3c73c8e83fa22d306cf75c92a6168659354f38d1c68e8e3ef310164166e3c7"` | | DNS only | Auto | 2026-10-08 22:19 | 2026-10-08 22:19 | `ae2a045c209a973ff6e0d4654ca6634a` |

Record 1 carries the comment "Placeholder; Cloudflare redirects www to
https://caelonk.me (rule redirect_www_to_apex)". No other record has a comment,
and no record has tags.

The zone's name servers are `damiete.ns.cloudflare.com` and
`naomi.ns.cloudflare.com`. They appear in the export below but not in the list,
because Cloudflare manages them itself.

## 2. What each group does

- **Website (records 1, 2, 9):** `caelonk.me` points at Railway, `www` is the
  proxied placeholder that Cloudflare redirects to the bare domain, and the
  `_railway-verify` TXT record proves ownership to Railway. A mail change
  should leave all three alone.
- **Mail (records 3 to 8):** the five MX records and the SPF record all belong
  to Namecheap's email forwarding (`registrar-servers.com`). They were imported
  when the zone was added to Cloudflare on 2026-10-06 and have not been edited
  since. These are the records a Zoho setup replaces.
- **Not present:** there is no DKIM record, no DMARC record (`_dmarc`), and no
  Zoho verification record.

## 3. Raw export (BIND zone file)

Output of `cf dns records export -z caelonk.me`, with Cloudflare's comment
header removed. Cloudflare stamped it `Exported: 2026-10-13 21:12:41`.

```text
;; SOA Record
caelonk.me	3600	IN	SOA	damiete.ns.cloudflare.com. dns.cloudflare.com. 2054359256 10000 2400 604800 3600

;; NS Records
caelonk.me.	86400	IN	NS	damiete.ns.cloudflare.com.
caelonk.me.	86400	IN	NS	naomi.ns.cloudflare.com.

;; A Records
www.caelonk.me.	1	IN	A	192.0.2.1 ; Placeholder; Cloudflare redirects www to https://caelonk.me (rule redirect_www_to_apex) cf_tags=cf-proxied:true

;; CNAME Records
caelonk.me.	1	IN	CNAME	l29it1kr.up.railway.app. ; cf_tags=cf-proxied:false

;; MX Records
caelonk.me.	1	IN	MX	20 eforward5.registrar-servers.com.
caelonk.me.	1	IN	MX	15 eforward4.registrar-servers.com.
caelonk.me.	1	IN	MX	10 eforward3.registrar-servers.com.
caelonk.me.	1	IN	MX	10 eforward2.registrar-servers.com.
caelonk.me.	1	IN	MX	10 eforward1.registrar-servers.com.

;; TXT Records
caelonk.me.	1	IN	TXT	"v=spf1 include:spf.efwd.registrar-servers.com ~all"
_railway-verify.caelonk.me.	1	IN	TXT	"railway-verify=ce3c73c8e83fa22d306cf75c92a6168659354f38d1c68e8e3ef310164166e3c7"
```
