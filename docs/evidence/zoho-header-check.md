# Zoho header check for `caelonk.me`

Header analysis for the Zoho guide. The sections below are carried over, unchanged apart from their numbers,
from the earlier full version of the Exercise 6 evidence (commit `e4f86dd`,
`docs/evidence/ex06.md`), which the three-item results sheet replaced in `bb57977`.
The short results are in [`ex06.md`](ex06.md). The DNS records are in
[`dns-before-zoho.md`](dns-before-zoho.md) and [`dns-after-zoho.md`](dns-after-zoho.md).

- **Domain address:** `caelon@caelonk.me` (Zoho Mail)
- **Outside mailbox:** a personal Gmail address, written as `<external Gmail>`
- **Times:** UTC unless a header shows its own zone

## 1. How SPF, DKIM and DMARC work here

**SPF** is one TXT policy listing the servers allowed to send mail for
`caelonk.me`. `include:zohomail.com` pulls in Zoho's published list of sending
servers. The receiver checks the address in the envelope sender (the
`Return-Path`), not the `From:` line people see. `~all` means "treat other
senders as suspicious" (softfail). `-all` means "reject them" (hardfail). The
guide uses `-all`. I left `~all` in place while testing. With DMARC in place,
either works, since DMARC decides the outcome. A hostname must have only one SPF
policy, because two `v=spf1` records make the SPF check fail. The domain has
one.

**DKIM** adds a signature to every message Zoho sends, covering the headers
(`From`, `To`, `Subject`, `Date`) and the body. The receiver uses the selector
(`s=zmail`) and domain (`d=caelonk.me`) to fetch the public key from DNS and
check the signature. A pass proves two things: the message hasn't changed in
transit, and it was signed by someone holding the domain's private key. That is
why a forged message can't simply copy the `From:` line. The **private key lives
on Zoho's sending servers**. It never appears in DNS, in this repository, or on
my laptop. Only the public half is published.

**DMARC** links those checks to the visible `From:` domain through
**alignment**. SPF aligns when the envelope sender's domain matches the `From:`
domain. DKIM aligns when the signature's `d=` domain matches it. A message
passes DMARC if SPF or DKIM passes **and** is aligned. `p=none` asks receivers
to deliver mail either way and report the results to the `rua` address, which
is `caelon@caelonk.me` on my own domain. Before publishing, `_dmarc` had no
record (before snapshot), so there was no stricter policy to keep. Once the
reports show clean results, the policy can move to `quarantine` and then
`reject`.


## 2. Delivery tests

| # | Test | Sender | Receiver | Time (UTC) | Observed result |
|---|---|---|---|---|---|
| 1 | Before setup | `<external Gmail>` | `caelon@caelonk.me` | 2026-10-13 21:09:06 | **Bounced** at 21:09:18. `Remote-MTA: eforward2.registrar-servers.com`, `554 5.7.1 <caelon@caelonk.me>: Relay access denied` |
| 2 | Incoming | `<external Gmail>` | `caelon@caelonk.me` | 2026-10-13 22:09:14 | **Received** in the Zoho inbox (I confirmed it in Zoho webmail on 2026-10-15). Gmail returned no bounce. I didn't save a screenshot; test 3's reply quotes this message's sender, date and subject |
| 3 | Reply from Zoho | `caelon@caelonk.me` (reply to test 2 in Zoho webmail) | `<external Gmail>` | 2026-10-15 18:57:30 | **Received** in the Gmail inbox at 18:57:35, in the same thread as test 2, `From: Caelon <caelon@caelonk.me>`. SPF, DKIM and DMARC passed (section 3) |
| 4 | New outgoing | `caelon@caelonk.me` (Zoho webmail) | `<external Gmail>` | 2026-10-13 21:56:09 | **Received** in the Gmail inbox at 21:56:12, `From: Caelon <caelon@caelonk.me>`. SPF and DKIM passed (section 3) |

**Test 1 timing.** It ran before any Zoho record existed (the verification TXT
came at 21:23), but the old Namecheap MX records were still published. So the
"before" result is Namecheap rejecting the message, not a missing MX record.

**Two more incoming attempts during the cutover** also bounced, from
`eforward1.registrar-servers.com` with the same `554 Relay access denied`: one
at 21:53:35 (bounce 21:53:46) and one at 21:55:28 (bounce 21:55:40). At that
point the Zoho and Namecheap MX records were both published, and `eforward1`
shared priority 10 with `mx.zoho.com`, so Gmail sometimes chose Namecheap.
*Investigation:* both bounce notices name the Namecheap server. An SMTP check
against `eforward1` reproduced the rejection without sending a message.
*Fix:* the five Namecheap MX records were deleted at 22:06. Test 2 was sent
after that, and no bounce came back.


## 3. Authentication results (tests 3 and 4)

Gmail lets me see the original message, headers included. In both excerpts the
external address and display name are redacted, routing IDs and signature data
are trimmed, and the body is removed.

### Test 3: reply from Zoho

```text
Return-Path: <caelon@caelonk.me>
Received: from sender6-of-o52.zoho.com (sender6-of-o52.zoho.com. [165.173.180.52])
        by mx.google.com with ESMTPS ... for <external Gmail>
        (version=TLS1_3 cipher=TLS_AES_256_GCM_SHA384 bits=256/256);
        Thu, 15 Oct 2026 11:57:35 -0700 (PDT)
Received-SPF: pass (google.com: domain of caelon@caelonk.me designates 165.173.180.52 as permitted sender) client-ip=165.173.180.52;
Authentication-Results: mx.google.com;
       dkim=pass header.i=@caelonk.me header.s=zmail header.b=Z8SIVwDW;
       arc=pass (i=1 spf=pass spfdomain=caelonk.me dkim=pass dkdomain=caelonk.me dmarc=pass fromdomain=caelonk.me>);
       spf=pass (google.com: domain of caelon@caelonk.me designates 165.173.180.52 as permitted sender) smtp.mailfrom=caelon@caelonk.me;
       dmarc=pass (p=NONE sp=NONE dis=NONE) header.from=caelonk.me
DKIM-Signature: v=1; a=rsa-sha256; q=dns/txt; c=relaxed/relaxed; s=zmail; d=caelonk.me; ...
Date: Thu, 15 Oct 2026 11:57:30 -0700
From: Caelon <caelon@caelonk.me>
To: <external Gmail>
In-Reply-To: <...@mail.gmail.com>
Subject: Re: Test 01
```

Here Gmail's own result includes `dmarc=pass (p=NONE ...)`. It found the
published `p=none` policy, and SPF and DKIM both passed aligned with
`caelonk.me`. `dis=NONE` means Gmail took no action against the message.

### Test 4: new outgoing message

```text
Return-Path: <caelon@caelonk.me>
Received: from sender5-of-o56.zoho.com (sender5-of-o56.zoho.com. [165.173.182.56])
        by mx.google.com with ESMTPS ... for <external Gmail>
        (version=TLS1_3 cipher=TLS_AES_256_GCM_SHA384 bits=256/256);
        Tue, 13 Oct 2026 14:56:12 -0700 (PDT)
Received-SPF: pass (google.com: domain of caelon@caelonk.me designates 165.173.182.56 as permitted sender) client-ip=165.173.182.56;
Authentication-Results: mx.google.com;
       dkim=pass header.i=@caelonk.me header.s=zmail header.b="AIcUEc/W";
       arc=pass (i=1 spf=pass spfdomain=caelonk.me dkim=pass dkdomain=caelonk.me dmarc=pass fromdomain=caelonk.me>);
       spf=pass (google.com: domain of caelon@caelonk.me designates 165.173.182.56 as permitted sender) smtp.mailfrom=caelon@caelonk.me
ARC-Authentication-Results: i=1; mx.zohomail.com;
	dkim=pass  header.i=caelonk.me;
	spf=pass  smtp.mailfrom=caelon@caelonk.me;
	dmarc=pass header.from=<caelon@caelonk.me>
DKIM-Signature: v=1; a=rsa-sha256; q=dns/txt; c=relaxed/relaxed; s=zmail; d=caelonk.me; ...
Date: Tue, 13 Oct 2026 14:56:09 -0700
From: Caelon <caelon@caelonk.me>
To: <external Gmail>
Subject: Test02
```

What this shows:

- **SPF passed** at Gmail. Zoho's server `165.173.182.56` is allowed by
  `include:zohomail.com`, and the envelope sender `caelon@caelonk.me` is on the
  same domain as `From:`, so SPF is aligned.
- **DKIM passed** at Gmail with `s=zmail` and `d=caelonk.me`. That means the
  public key published at `zmail._domainkey` matches the private key Zoho
  signed with. The signing domain is the `From:` domain, so DKIM is aligned.
- **DMARC:** Gmail's own `Authentication-Results` line has no separate `dmarc=`
  entry for test 4. The `dmarc=pass` results come from the ARC chain: Zoho's own
  check (`i=1`), which Gmail repeats in its `arc=pass` summary. Test 4 was sent
  at 21:56 on 2026-10-13, before the `_dmarc` record was published at 22:01.
  That likely explains the missing result. Test 3, sent after the record existed,
  shows Gmail's own `dmarc=pass`.
- These results cover tests 3 and 4 only. A record existing in DNS doesn't prove
  that any other message passed.

## 4. Zoho verification states and what is still open

| Check | State | Evidence |
|---|---|---|
| Domain ownership (TXT) | **Verified** | Zoho email to `<external Gmail>`, 2026-10-13 21:24:43: "The domain caelonk.me has been updated as verified in your organization" |
| MX (`mx`, `mx2`, `mx3.zoho.com` at 10, 20, 50) | **Verified** (green check on all three) | Admin Console screenshot below, taken 2026-10-15 |
| SPF (`v=spf1 include:zohomail.com ~all`) | **Verified** | Same screenshot |
| DKIM (`zmail._domainkey`) | **Verified** | Same screenshot; its key matches the published record |
| DKIM signing | Working in practice | Gmail `dkim=pass s=zmail` on tests 3 and 4 |
| Incoming mail (MX) | Working in practice | Test 2 received in Zoho |

![Zoho Admin Console, DNS records for caelonk.me: MX, SPF and DKIM all verified](ex06-zoho-dns.png)

The screenshot shows only DNS values and states, with no personal details. It
doesn't cover DMARC, which this page doesn't list.

**Left out on purpose:** reading the DMARC aggregate reports that receivers
send to `caelon@caelonk.me`. The exercise doesn't require it. DMARC results for
individual messages are in section 3.

