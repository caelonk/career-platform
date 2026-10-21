# Live checks: DNS, HTTPS and the `www` redirect

Run from the laptop on **2026-10-21 at 04:12 UTC** (2026-10-20, 21:12 Pacific).
Read-only: nothing was changed.

```bash
nslookup caelonk.me 1.1.1.1
nslookup www.caelonk.me 1.1.1.1
echo | openssl s_client -connect caelonk.me:443 -servername caelonk.me 2>/dev/null \
  | openssl x509 -noout -subject -issuer -dates -ext subjectAltName
curl -s -D - -o page.html https://caelonk.me/
curl -s -o /dev/null -w '%{http_code} %{redirect_url}' <each URL below>
curl -s -L -o /dev/null -w '%{http_code} %{url_effective} hops=%{num_redirects} ssl_verify=%{ssl_verify_result}' http://www.caelonk.me/
```

## DNS (resolver `1.1.1.1`)

| Name | Answer | Meaning |
|---|---|---|
| `caelonk.me` | `69.46.46.62` | The apex `CNAME → l29it1kr.up.railway.app` (DNS only), flattened by Cloudflare into Railway's edge address |
| `www.caelonk.me` | `172.67.175.67`, `104.21.31.73` and two IPv6 addresses | Cloudflare proxy addresses: the `www` record is proxied so Cloudflare can answer the redirect |

Neither name points at the Azure VM (`52.162.50.66`).

## Certificate for `caelonk.me` (served by Railway)

| Item | Value |
|---|---|
| Subject | `CN=caelonk.me` |
| Names (SAN) | `caelonk.me` |
| Issuer | Let's Encrypt, intermediate `YE2` |
| Valid | 2026-10-08 21:23:16 UTC to **2027-01-06 21:23:15 UTC** (90 days) |
| `openssl` verify | `Verify return code: 0 (ok)` |

Railway obtained this certificate after `caelonk.me` was added to the service as a custom
domain on 2026-10-08 (Railway plan, R4 results). Let's Encrypt dates certificates about
an hour before issue, which is why `notBefore` is earlier than the domain's 22:16 UTC
creation time. Railway renews it; there is nothing for me to run. That depends on the
apex record still pointing at Railway **DNS only**, because Let's Encrypt has to reach
Railway to validate the name. Railway's exact renewal timing isn't recorded here, and no
renewal can be observed before it happens; the check to repeat is the `openssl` command
above, before 2027-01-06.

## Certificate for `www.caelonk.me` (served by Cloudflare)

| Item | Value |
|---|---|
| Subject / names | `CN=caelonk.me`, SAN `*.caelonk.me`, `caelonk.me` |
| Issuer | Let's Encrypt `YE2` |
| Valid | 2026-10-06 00:57:07 UTC to 2027-01-04 00:57:06 UTC |

This is Cloudflare's edge certificate for the proxied `www` record (it covers
`*.caelonk.me`), issued and renewed by Cloudflare.

## Responses

| Request | Result | Pass |
|---|---|---|
| `https://caelonk.me/` | `HTTP/1.1 200 OK`, `Server: railway-hikari`, `x-railway-edge: lax1`; my name appears 5 times | Yes |
| `http://caelonk.me/` | `301` → `https://caelonk.me/` | Yes |
| `http://www.caelonk.me/` | `301` → `https://caelonk.me/` | Yes |
| `https://www.caelonk.me/` | `301` → `https://caelonk.me/` | Yes |
| `https://www.caelonk.me/projects/legal-document-analyzer?x=1` | `301` → `https://caelonk.me/projects/legal-document-analyzer?x=1` (path and query kept) | Yes |
| `http://www.caelonk.me/`, following redirects | Ends at `https://caelonk.me/` with `200`, 1 redirect, certificate verified (`ssl_verify_result=0`) | Yes |
