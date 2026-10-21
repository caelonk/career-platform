# Azure VM deployment (as built)

The Azure VM served `caelonk.me` from 2026-10-05 until the move to Railway on 2026-10-10.
It has been deallocated since 2026-10-13 and is kept as the rollback copy. Earlier
versions of this runbook described Azure Database for PostgreSQL and a dedicated
`career-platform` service user; neither was built.

| Part | As built |
|---|---|
| VM | `vm-career-platform` in `rg-career-platform`, `northcentralus`, `Standard_B2ats_v2`, Ubuntu 24.04 |
| Addresses | Public `52.162.50.66` (static, held by Azure), private `10.0.0.4` |
| SSH | Key only, user `azureuser`, from the operator laptop's `/32` (NSG `Allow-SSH-Laptop`, priority 300) |
| Web | NSG `Allow-HTTP-80` (320) and `Allow-HTTPS-443` (330) from anyone; everything else hits `DenyAllInBound` |
| Nginx | [`deploy/nginx/career-platform.conf`](../nginx/career-platform.conf), plus Certbot's HTTPS changes |
| App | [`deploy/systemd/career-platform.service`](../systemd/career-platform.service): Uvicorn, 2 workers, `127.0.0.1:8000`, as `azureuser` |
| Database | SQLite at `/home/azureuser/career-platform/career_platform.db`, read only by the app on the same VM |
| Certificate | Let's Encrypt for `caelonk.me` and `www.caelonk.me`, renewed by `certbot.timer` |

## Where the steps and results are

1. First deployment, tunnel access only: [`docs/superpowers/plans/2026-09-24-azure-vm-migration.md`](../../docs/superpowers/plans/2026-09-24-azure-vm-migration.md) and [`docs/evidence/ex03.md`](../../docs/evidence/ex03.md)
2. systemd, Nginx, network rules, restart and crash tests, domain: [`docs/superpowers/plans/2026-10-01-operate-the-vm.md`](../../docs/superpowers/plans/2026-10-01-operate-the-vm.md)
3. HTTPS, renewal, open ports: [`docs/how-this-site-is-secured.md`](../../docs/how-this-site-is-secured.md)
4. Move to Railway and deallocation: [`docs/superpowers/plans/2026-10-08-railway-postgres-migration.md`](../../docs/superpowers/plans/2026-10-08-railway-postgres-migration.md)

[`docs/superpowers/plans/2026-09-29-azure-vm-provisioning.md`](../../docs/superpowers/plans/2026-09-29-azure-vm-provisioning.md)
(VM template as code and a bootstrap script) was written but **not carried out**. The VM
was built by hand as described above.

## Bringing it back (rollback)

Start the VM in the portal. systemd starts Uvicorn and Nginx at boot (shown in the
operate-the-VM plan, Restart 1). Then follow the rollback in the
[README](../../README.md#rollback). The VM's SQLite database is frozen at its 2026-10-08
state.
