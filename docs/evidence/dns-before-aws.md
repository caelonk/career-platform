# Cloudflare DNS for caelonk.me before the AWS test record

Read 2026-11-02 with `cf dns records list --zone caelonk.me`, before adding `aws.caelonk.me` (AWS plan Task 7).

| Type | Name | Content | Priority | Proxy |
|---|---|---|---|---|
| A | www.caelonk.me | `192.0.2.1` |  | proxied |
| CNAME | caelonk.me | `l29it1kr.up.railway.app` |  | DNS only |
| MX | caelonk.me | `mx.zoho.com` | 10 | DNS only |
| MX | caelonk.me | `mx2.zoho.com` | 20 | DNS only |
| MX | caelonk.me | `mx3.zoho.com` | 50 | DNS only |
| TXT | _dmarc.caelonk.me | `"v=DMARC1; p=none; rua=mailto:caelon@caelonk.me"` |  | DNS only |
| TXT | _railway-verify.caelonk.me | `"railway-verify=ce3c73c8e83fa22d306cf75c92a6168659354f38d1c68e8e3ef310` |  | DNS only |
| TXT | caelonk.me | `"v=spf1 include:zohomail.com ~all"` |  | DNS only |
| TXT | caelonk.me | `"zoho-verification=zb04468953.zmverify.zoho.com"` |  | DNS only |
| TXT | zmail._domainkey.caelonk.me | `"v=DKIM1; k=rsa; p=MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQCW0hAazTaDOiN` |  | DNS only |
