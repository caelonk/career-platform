# How this site is secured

How `https://caelonk.me` is protected: its certificate, how the certificate renews, which ports are open, and where encryption starts and ends. Checked on the VM `vm-career-platform` on 2026-10-08 (UTC).

## 1. The certificate

| Item | Value |
|---|---|
| Issuer | Let's Encrypt, intermediate `YE1` (`C = US, O = Let's Encrypt, CN = YE1`) |
| Subject | `CN = caelonk.me` |
| Names covered (Subject Alternative Name) | `caelonk.me`, `www.caelonk.me` |
| Valid from | 2026-10-06 21:03:33 UTC |
| Expires | **2027-01-04 21:03:32 UTC** (90-day certificate) |
| Key type | ECDSA |
| Files on the VM | `/etc/letsencrypt/live/caelonk.me/fullchain.pem` and `privkey.pem` |

Nginx serves this certificate on port 443. `sudo certbot certificates` and `openssl x509` on the certificate file give the same values.

## 2. Renewal

**How it works**

- Certbot installed a systemd timer, `certbot.timer`.
- The timer runs twice a day (`OnCalendar=*-*-* 00,12:00:00`). Each run is delayed by a random amount up to 12 hours (`RandomizedDelaySec=43200`), so renewal requests from many servers don't all reach Let's Encrypt at the same moment.
- Each run starts `certbot -q renew`. That command only replaces a certificate once it's within about 30 days of expiring, so this one should renew around early December 2026.
- To renew, Certbot uses Nginx to prove it controls the domain (`authenticator = nginx`). It then installs the new certificate and reloads Nginx (`installer = nginx`).
- No one has to do anything by hand.

**Renewal test** (`sudo certbot renew --dry-run`, 2026-10-08 04:27 UTC)

- A dry run goes through the full renewal against Let's Encrypt but keeps the current certificate.
- It ran for both `caelonk.me` and `www.caelonk.me`.
- Result: `Congratulations, all simulated renewals succeeded` and `no renewal failures`.

**Timer check** (`systemctl list-timers certbot.timer`, `systemctl is-enabled` and `systemctl is-active certbot.timer`)

| Check | Result |
|---|---|
| Enabled at boot | `enabled` |
| Running now | `active` |
| Last run | 2026-10-08 03:20:51 UTC |
| Next run | 2026-10-08 20:47:01 UTC |

## 3. Ports open to the internet

The Azure network security group `vm-career-platformNSG` decides what reaches the VM. Ubuntu's own firewall, `ufw`, is not enabled.

| Port | NSG rule (priority) | Who can connect | Why it's open |
|---|---|---|---|
| 22/TCP (SSH) | `Allow-SSH-Laptop` (300) | **Only my laptop's single public IP (`/32`)** | So I can manage the VM. Logging in also needs my SSH key. `sshd` has password logins off (`passwordauthentication no`, `pubkeyauthentication yes`), and root can't log in with a password (`permitrootlogin without-password`). |
| 80/TCP (HTTP) | `Allow-HTTP-80` (320) | Anyone | Redirects only. `http://caelonk.me` returns `301` to `https://`, so anyone who types the plain address ends up on the secure site. A request to the bare IP gets a `404`. Let's Encrypt's domain checks also come in on this port. |
| 443/TCP (HTTPS) | `Allow-HTTPS-443` (330) | Anyone | The site itself, served over HTTPS. |

The NSG drops everything else with Azure's default `DenyAllInBound` rule. That includes the app's port 8000, which has no NSG rule. The app also listens only on `127.0.0.1:8000`, so it can't be reached from outside the VM even if a firewall rule were wrong.

What's listening on the VM (`sudo ss -ltnp`):

| Address:port | Program |
|---|---|
| `0.0.0.0:22`, `[::]:22` | `sshd` |
| `0.0.0.0:80`, `[::]:80` | `nginx` |
| `0.0.0.0:443`, `[::]:443` | `nginx` |
| `127.0.0.1:8000` | `uvicorn` (the app; reachable only from inside the VM) |
| `127.0.0.53:53`, `127.0.0.54:53` | `systemd-resolved` (Ubuntu's local DNS helper; reachable only from inside the VM) |

## 4. Where encryption starts and ends

```
Browser ──HTTPS (TLS, encrypted)──▶ Azure public IP 52.162.50.66 ──▶ VM 10.0.0.4
                                                                       │
                                                         Nginx :443 ◀──┘  TLS ends here
                                                                       │
                                               plain HTTP over loopback │
                                                                       ▼
                                                      Uvicorn 127.0.0.1:8000 (the app)
```

- **Starts:** in the visitor's browser, which encrypts the request with TLS.
- **Over the internet:** the request stays encrypted on its way to Azure's public IP, which forwards it to the VM's private address. Azure doesn't decrypt it.
- **Ends:** at **Nginx on the VM**, port 443. Nginx holds the private key (`privkey.pem`) and decrypts the request there.
- **Nginx to the app:** `proxy_pass http://127.0.0.1:8000` is **plain HTTP, not encrypted**. That's acceptable because the traffic never leaves the VM: it goes over the loopback interface, which nothing on the network can see.
- **Telling the app:** Nginx adds `X-Forwarded-Proto: https`, so the app knows the original request was encrypted. It also adds `X-Forwarded-For` and `X-Real-IP` so the app sees the visitor's address.
- **Plain HTTP visitors:** the port 80 server block sends them a `301` to HTTPS before any content is served.

## 5. Checking the certificate in Chrome

1. Open `https://caelonk.me`.
2. Click the icon to the left of the domain in the address bar.
3. Click **Connection is secure**.
4. Click **Certificate is valid**.

The certificate viewer should show:

- **Issued To:** Common Name `caelonk.me`
- **Issued By:** Let's Encrypt, Common Name `YE1`
- **Validity period:** Oct 6, 2026 to Jan 4, 2027
- **Details tab:** under Subject Alternative Name, both `caelonk.me` and `www.caelonk.me`

If you're on a network with a web filter, such as campus Wi-Fi, it may block the site. Use a phone on cellular data instead.

## Evidence: checks run from the VM

I ran these over SSH on the VM. The requests went out to the public address and came back in, so they follow the same path visitors use.

```bash
curl -I http://caelonk.me
curl -sS -D - -o /dev/null https://caelonk.me
openssl s_client -connect caelonk.me:443 -servername caelonk.me </dev/null 2>/dev/null | openssl x509 -noout -subject -issuer -dates
```

The HTTPS check uses `-D - -o /dev/null` (a normal `GET` that prints only the headers) instead of `-I`. `-I` sends `HEAD`, which the app answers with `405` because its routes only accept `GET`. The HTTP check can use `-I`, because Nginx sends the redirect itself and never passes the request to the app.

Output (2026-10-08 04:37 UTC):

```
HTTP/1.1 301 Moved Permanently
Server: nginx/1.24.0 (Ubuntu)
Date: Thu, 08 Oct 2026 04:37:05 GMT
Content-Type: text/html
Content-Length: 178
Connection: keep-alive
Location: https://caelonk.me/

HTTP/1.1 200 OK
Server: nginx/1.24.0 (Ubuntu)
Date: Thu, 08 Oct 2026 04:37:05 GMT
Content-Type: text/html; charset=utf-8
Content-Length: 4611
Connection: keep-alive

subject=CN = caelonk.me
issuer=C = US, O = Let's Encrypt, CN = YE1
notBefore=Oct  6 21:03:33 2026 GMT
notAfter=Jan  4 21:03:32 2027 GMT
```

| Check | Expected | Actual | Result |
|---|---|---|---|
| HTTP redirects to HTTPS | `301` to `https://caelonk.me/` | `301 Moved Permanently`, `Location: https://caelonk.me/` | Pass |
| HTTPS serves the site | `200` from Nginx | `200 OK`, `Server: nginx/1.24.0 (Ubuntu)`, `text/html` | Pass |
| Certificate subject | `CN = caelonk.me` | `CN = caelonk.me` | Pass |
| Certificate issuer | Let's Encrypt | `O = Let's Encrypt, CN = YE1` | Pass |
| Certificate dates | Valid now, about 90 days | 2026-10-06 to 2027-01-04 | Pass |
