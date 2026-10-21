# Project 1 submission: Own Your Corner of the Internet

| | |
|---|---|
| Repository | <https://github.com/caelonk/career-platform> |
| Live site | <https://caelonk.me> |
| Final commit | [`8d76e16`](https://github.com/caelonk/career-platform/commit/8d76e166e5fe980fe0aada7dea953d6ee5c24d82), deployed on Railway as `4acbe4be` on 2026-10-21. One docs-only commit follows it, adding this line and updating `TASKS.md` |
| Explanation of the system | [README](../README.md) |

Items marked **gap** or **unverified** are known to be missing or unchecked.

## 1. README, original spec and plans

- [README](../README.md)
- Original spec: [`superpowers/specs/2026-09-15-personal-career-platform-design.md`](superpowers/specs/2026-09-15-personal-career-platform-design.md)
- Application plan: [`superpowers/plans/2026-09-15-personal-career-platform.md`](superpowers/plans/2026-09-15-personal-career-platform.md)
- Azure plans: [`2026-09-24-azure-vm-migration.md`](superpowers/plans/2026-09-24-azure-vm-migration.md), [`2026-10-01-operate-the-vm.md`](superpowers/plans/2026-10-01-operate-the-vm.md), and [`2026-09-29-azure-vm-provisioning.md`](superpowers/plans/2026-09-29-azure-vm-provisioning.md) (written, not carried out)
- Railway plan: [`2026-10-08-railway-postgres-migration.md`](superpowers/plans/2026-10-08-railway-postgres-migration.md)
- Application behavior with a database outage: [`evidence/database-outage-check.md`](evidence/database-outage-check.md), tests in [`tests/routes/test_database_outage.py`](../tests/routes/test_database_outage.py)

## 2. Diagrams, including email and analytics

- Railway, email and analytics: [README, "How it runs now"](../README.md#how-it-runs-now-railway)
- Azure VM: [README, "How it ran before"](../README.md#how-it-ran-before-azure-vm)
- Request path step by step: [`midterm-request-path.md`](midterm-request-path.md)

## 3. Migration plan, data comparison, cutover and rollback

- Plan with dependency inventory and dated results: [Railway plan](superpowers/plans/2026-10-08-railway-postgres-migration.md) (Facts, Tasks 1–6)
- What Git moved and what it didn't: Railway plan, "Added afterward (2026-10-20)"
- Source/target comparison: Railway plan D2–D3 (every row of 13 tables), and the rendered pages compared on 2026-10-21 in [`evidence/azure-vm-check-2026-10-21.md`](evidence/azure-vm-check-2026-10-21.md)
- **Gap:** no deliberate change to the original data before the copy (Railway plan, "Added afterward")
- Cutover and checks after it: Railway plan R4, V1–V3, Domain, S1
- Rollback for code, data and back to the VM: [README, "Rollback"](../README.md#rollback)
- Responsibilities on Azure versus Railway: [README, "Who manages what"](../README.md#who-manages-what)

## 4. Azure HTTP and restart evidence, final DNS and HTTPS

- First deployment: [`evidence/ex03.md`](evidence/ex03.md), Azure migration plan "Verify"
- systemd, Nginx, NSG, addresses, ports, and restart and crash tests (2026-10-05): [operate-the-VM plan](superpowers/plans/2026-10-01-operate-the-vm.md) sections 2–7
- Boot check, ports, NSG and certificate after restarting the VM (2026-10-21): [`evidence/azure-vm-check-2026-10-21.md`](evidence/azure-vm-check-2026-10-21.md)
- Deploy files as built: [`deploy/`](../deploy/azure/README.md)
- VM HTTPS, certificate and renewal (2026-10-08): [`how-this-site-is-secured.md`](how-this-site-is-secured.md)
- Final DNS, Railway certificate and `www` redirects (2026-10-21): [`evidence/live-checks-2026-10-21.md`](evidence/live-checks-2026-10-21.md)
- DNS records: [`evidence/dns-before-zoho.md`](evidence/dns-before-zoho.md), [`evidence/dns-after-zoho.md`](evidence/dns-after-zoho.md)

## 5. Reviewed commit, its Railway deployment, and the live change

- [`evidence/reviewed-change.md`](evidence/reviewed-change.md)
- Recovery for code and data: [README, "Rollback"](../README.md#rollback)

## 6. Zoho sending, receiving, replying and DNS authentication

- Results sheet, including the message sent before MX: [`evidence/ex06.md`](evidence/ex06.md) sections 1–2
- Header analysis: [`evidence/zoho-header-check.md`](evidence/zoho-header-check.md)
- Records before and after: [`evidence/dns-before-zoho.md`](evidence/dns-before-zoho.md), [`evidence/dns-after-zoho.md`](evidence/dns-after-zoho.md)

## 7. GA4 page view and interaction

- Realtime screenshot, the action taken, and how collection works: [`evidence/ex06.md`](evidence/ex06.md) sections 3–4
- The tag: [`app/templates/base.html`](../app/templates/base.html); the opt-out: [Privacy page](https://caelonk.me/privacy)

## 8. Failures, decisions, reflection, costs and limitations

- Failures: [README, "Failures investigated"](../README.md#failures-investigated), including [`evidence/ex03.md`](evidence/ex03.md), [`evidence/ex05.md`](evidence/ex05.md) (lab simulation) and [`evidence/database-outage-check.md`](evidence/database-outage-check.md)
- Decisions: [README, "Decisions"](../README.md#decisions)
- Reflection: [README, "Reflection"](../README.md#reflection)
- Costs, expiry and cleanup: [README, "Costs, expiry and cleanup"](../README.md#costs-expiry-and-cleanup)
- Limitations: [README, "Limitations"](../README.md#limitations)
- My HTTPS explanation for Exercise 4: [`how-this-site-is-secured.md`](how-this-site-is-secured.md)
