# DNS records for `caelonk.me` after the Zoho Mail setup

Snapshot taken **2026-10-13 22:06 UTC**, after the mail records were switched
from Namecheap email forwarding to Zoho Mail. The state before the change is in
[`dns-before-zoho.md`](dns-before-zoho.md).

- **Source:** Cloudflare, the authoritative DNS host for the zone, read through
  the Cloudflare CLI (`cf` 1.0.0-beta.13, logged in as the Owner).
- **Scope:** every record in the zone. The list returned 10 records with a page
  size of 100, so nothing was cut off by paging.
- **Public check:** the mail records and `www` were also looked up on Google's
  resolver (`8.8.8.8`) with `Resolve-DnsName`. Results are in section 4.

```text
cf dns records list -z caelonk.me --per-page 100 --order type
cf dns records export -z caelonk.me
```

## 1. Records

A TTL of `1` is how Cloudflare writes "Auto".

| # | Type | Name | Content | Priority | Proxy | TTL | Created (UTC) | Modified (UTC) | Record ID |
|---|---|---|---|---|---|---|---|---|---|
| 1 | A | `www.caelonk.me` | `192.0.2.1` | | Proxied | Auto | 2026-10-06 01:38 | 2026-10-13 22:04 | `de02731044ebf21564d2e597c258e4bb` |
| 2 | CNAME | `caelonk.me` | `l29it1kr.up.railway.app` | | DNS only | Auto | 2026-10-08 22:18 | 2026-10-08 22:18 | `54c95a56c5bbe19571e74a9bad3a5569` |
| 3 | MX | `caelonk.me` | `mx.zoho.com` | 10 | DNS only | Auto | 2026-10-13 21:35 | 2026-10-13 21:35 | `abfc41918b3d839a4aca2a930281357f` |
| 4 | MX | `caelonk.me` | `mx2.zoho.com` | 20 | DNS only | Auto | 2026-10-13 21:36 | 2026-10-13 21:36 | `c684b7dfcf6088b3862497a0ae7b2fd4` |
| 5 | MX | `caelonk.me` | `mx3.zoho.com` | 50 | DNS only | Auto | 2026-10-13 21:36 | 2026-10-13 21:36 | `b2c85a2c32f29ecb1296ae0e3e85e053` |
| 6 | TXT | `caelonk.me` | `"v=spf1 include:zohomail.com ~all"` | | DNS only | Auto | 2026-10-06 01:34 | 2026-10-13 21:37 | `2580d0e19ae2fd04150aa4a83c28a08d` |
| 7 | TXT | `caelonk.me` | `"zoho-verification=zb04468953.zmverify.zoho.com"` | | DNS only | Auto | 2026-10-13 21:23 | 2026-10-13 21:23 | `c4a5b7bd4e0a5d4066fcdd3a7c559938` |
| 8 | TXT | `_dmarc.caelonk.me` | `"v=DMARC1; p=none; rua=mailto:caelon@caelonk.me"` | | DNS only | Auto | 2026-10-13 22:01 | 2026-10-13 22:01 | `cd536c93bdeb23b265ae65755cded0fc` |
| 9 | TXT | `_railway-verify.caelonk.me` | `"railway-verify=ce3c73c8e83fa22d306cf75c92a6168659354f38d1c68e8e3ef310164166e3c7"` | | DNS only | Auto | 2026-10-08 22:19 | 2026-10-08 22:19 | `ae2a045c209a973ff6e0d4654ca6634a` |
| 10 | TXT | `zmail._domainkey.caelonk.me` | `"v=DKIM1; k=rsa; p=MIGfMA0G...canQIDAQAB"` (full key in section 5) | | DNS only | Auto | 2026-10-13 21:37 | 2026-10-13 21:37 | `1b63c0cb59c0fe3b077bfcee63b8d744` |

Record 1 carries the comment "Placeholder; Cloudflare redirects www to
https://caelonk.me (rule redirect_www_to_apex)". No other record has a comment,
and no record has tags.

The zone's name servers are still `damiete.ns.cloudflare.com` and
`naomi.ns.cloudflare.com`.

## 2. What changed since the "before" snapshot

| Change | Record | Who | When (UTC) |
|---|---|---|---|
| Added | TXT `caelonk.me` Zoho verification code | Owner | 21:23 |
| Added | MX `mx.zoho.com` 10, `mx2.zoho.com` 20, `mx3.zoho.com` 50 | Owner | 21:35 to 21:36 |
| Edited in place | SPF, from `include:spf.efwd.registrar-servers.com` to `include:zohomail.com` (same record ID) | Owner | 21:37 |
| Added | TXT `zmail._domainkey` DKIM key | Owner | 21:37 |
| Added | TXT `_dmarc` DMARC policy | Owner | 22:01 |
| Deleted | MX `eforward1` to `eforward5.registrar-servers.com` (Namecheap forwarding) | Agent, with `cf dns records delete` | 22:06 |

The website records (2 and 9) are untouched. Record 1 (`www`) ends in the same
state as before, proxied with the same content. It was DNS only between 21:23
and 22:04, and during that time `https://www.caelonk.me/` timed out instead of
redirecting.

**Why deleting the Namecheap MX records was safe:** before deleting them, an
SMTP conversation with `eforward1.registrar-servers.com` (no message sent)
answered `554 5.7.1 <caelon@caelonk.me>: Relay access denied`. Namecheap was not
accepting mail for the domain, so those records could only cause bounces.

## 3. Comparison with what Zoho expects

The "Zoho expects" column is Zoho's standard setup for its US data center
(`zoho.com`). It was not read from the Zoho admin console.

| Record | Published | Zoho expects | Result |
|---|---|---|---|
| MX | `mx.zoho.com` 10, `mx2.zoho.com` 20, `mx3.zoho.com` 50, nothing else | Exactly those three | Match |
| SPF | `v=spf1 include:zohomail.com ~all`, one SPF record | The same, and only one SPF record | Match |
| DKIM | TXT at `zmail._domainkey`, `v=DKIM1; k=rsa`, 1024-bit key | A TXT at the chosen selector holding the key Zoho generated | Present and well-formed. The key value was not compared with the console |
| DMARC | `v=DMARC1; p=none; rua=mailto:caelon@caelonk.me` | A valid DMARC record; `p=none` is the usual first policy | Match |
| Verification | `zoho-verification=zb04468953.zmverify.zoho.com` | The code shown in the console | Present. The code was not compared with the console |

Not yet shown by this evidence: that the `caelon@caelonk.me` mailbox receives
mail, and that Zoho's console reports DKIM as verified.

**Follow-up (2026-10-21):** both are now shown elsewhere. Mail is received
(`ex06.md`, section 1), and Zoho's Admin Console shows the domain, MX, SPF and
DKIM as verified (screenshot `ex06-zoho-dns.png`, 2026-10-15; domain status
checked again by the Owner on 2026-10-21: Verified). The published DKIM key and
verification code were not compared with the console character by character;
Zoho's verified status means its own lookup of the published records matched.

## 4. Public resolver check (`8.8.8.8`)

Run with `Resolve-DnsName <name> -Type <type> -Server 8.8.8.8 -DnsOnly`,
between 22:06 and 22:07 UTC.

| Lookup | Answer | Matches Cloudflare |
|---|---|---|
| MX `caelonk.me` | `mx.zoho.com` 10, `mx2.zoho.com` 20, `mx3.zoho.com` 50 | Yes |
| TXT `caelonk.me` | `v=spf1 include:zohomail.com ~all` and `zoho-verification=zb04468953.zmverify.zoho.com` | Yes |
| TXT `_dmarc.caelonk.me` | `v=DMARC1; p=none; rua=mailto:caelon@caelonk.me` | Yes |
| TXT `zmail._domainkey.caelonk.me` | The DKIM key in section 5 | Yes |
| A `www.caelonk.me` | `104.21.31.73`, `172.67.175.67` (Cloudflare proxy addresses) | Yes |

Two of these took a moment to settle, because the records use a 5-minute TTL:

- One MX lookup at 22:06:50, seconds after the deletion, still returned the five
  Namecheap hosts from cache. Seven later lookups returned only the Zoho hosts.
- `www` returned the old `192.0.2.1` until its cached answer expired at about
  22:07:20, then returned the Cloudflare addresses.

Both Cloudflare name servers (`naomi` and `damiete`) returned only the three
Zoho MX hosts throughout. After the cache cleared,
`curl -sI https://www.caelonk.me/` returned `301` with
`Location: https://caelonk.me/` and `Server: cloudflare`.

## 5. Raw export (BIND zone file)

Output of `cf dns records export -z caelonk.me`, with Cloudflare's comment
header removed. Cloudflare stamped it `Exported: 2026-10-13 22:06:50`.

```text
;; SOA Record
caelonk.me	3600	IN	SOA	damiete.ns.cloudflare.com. dns.cloudflare.com. 2054359581 10000 2400 604800 3600

;; NS Records
caelonk.me.	86400	IN	NS	damiete.ns.cloudflare.com.
caelonk.me.	86400	IN	NS	naomi.ns.cloudflare.com.

;; A Records
www.caelonk.me.	1	IN	A	192.0.2.1 ; Placeholder; Cloudflare redirects www to https://caelonk.me (rule redirect_www_to_apex) cf_tags=cf-proxied:true

;; CNAME Records
caelonk.me.	1	IN	CNAME	l29it1kr.up.railway.app. ; cf_tags=cf-proxied:false

;; MX Records
caelonk.me.	1	IN	MX	50 mx3.zoho.com.
caelonk.me.	1	IN	MX	20 mx2.zoho.com.
caelonk.me.	1	IN	MX	10 mx.zoho.com.

;; TXT Records
caelonk.me.	1	IN	TXT	"v=spf1 include:zohomail.com ~all"
caelonk.me.	1	IN	TXT	"zoho-verification=zb04468953.zmverify.zoho.com"
_dmarc.caelonk.me.	1	IN	TXT	"v=DMARC1; p=none; rua=mailto:caelon@caelonk.me"
_railway-verify.caelonk.me.	1	IN	TXT	"railway-verify=ce3c73c8e83fa22d306cf75c92a6168659354f38d1c68e8e3ef310164166e3c7"
zmail._domainkey.caelonk.me.	1	IN	TXT	"v=DKIM1; k=rsa; p=MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQCW0hAazTaDOiNVreyygkhMS+MZQP1h+q3kh7YAeUqbNOyFwRthI4m1+QekKs2/RlixRRW77jUOE/eYnDXXVO3vXpLPSV3csuf0IOWUx5iyig+BVASfXLrGkUwkswl0DKIEHH2mbYIZKJa/TrD4+Fr30enjdZ8zMk7YG01ZufcanQIDAQAB"
```
