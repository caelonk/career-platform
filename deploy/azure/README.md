# Azure deployment runbook

This runbook covers the Azure Linux VM + Nginx + systemd deployment for the personal career platform.

## VM hardening
- Create a Linux VM with a non-root service account named `career-platform`.
- Allow SSH only from the admin IP range and permit HTTP/HTTPS from the internet.
- Configure automatic security updates and disable direct root login.

## Database and networking
- Use Azure Database for PostgreSQL Flexible Server for the production database.
- Allow only the VM subnet and required operator addresses to reach the database.
- Store the production database URL in `/etc/career-platform/.env` with restricted file permissions.

## TLS and reverse proxy
- Install Nginx and TLS certificates from Let's Encrypt or Azure-managed certificates.
- Copy `deploy/nginx/career-platform.conf` to `/etc/nginx/conf.d/career-platform.conf`.
- Verify the config with `sudo nginx -t` and reload Nginx.

## Service setup
- Install the Python environment on the VM and deploy the release.
- Copy `deploy/systemd/career-platform.service` to `/etc/systemd/system/career-platform.service`.
- Enable the service with `sudo systemctl daemon-reload && sudo systemctl enable --now career-platform`.

## Operations
- Run migrations with `alembic upgrade head` before deployment.
- Keep the latest valid snapshot in `/srv/career-platform/snapshots` and ensure the service user owns the directory.
- For rollback, restore the previous application release and previous snapshot directory, then restart the service.
