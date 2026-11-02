from __future__ import annotations

import json
from pathlib import Path


def test_nginx_config_is_the_vm_front_door():
    # The site file as copied from the Azure VM on 2026-10-21.
    config = Path("deploy/nginx/career-platform.conf").read_text()
    assert "listen 80 default_server;" in config
    assert "listen 443 ssl;" in config
    assert "return 301 https://$host$request_uri;" in config
    assert "proxy_pass http://127.0.0.1:8000;" in config
    assert "proxy_set_header X-Forwarded-Proto $scheme;" in config


def test_systemd_service_matches_the_vm_unit():
    # The unit as installed on the Azure VM on 2026-10-05.
    unit = Path("deploy/systemd/career-platform.service").read_text()
    assert "User=azureuser" in unit
    assert "WorkingDirectory=/home/azureuser/career-platform" in unit
    assert "--host 127.0.0.1 --port 8000 --workers 2" in unit
    assert "Restart=on-failure" in unit
    assert "WantedBy=multi-user.target" in unit


def test_dockerfile_serves_on_railway_port_behind_proxy():
    dockerfile = Path("Dockerfile").read_text()
    assert "uv sync --locked --no-dev" in dockerfile
    assert "${PORT:-8000}" in dockerfile
    assert "--proxy-headers" in dockerfile
    assert "--forwarded-allow-ips" in dockerfile
    for path in ("alembic.ini", "migrations", "scripts"):
        assert f"COPY {path}" in dockerfile


def test_railway_config_migrates_before_deploy_and_health_checks():
    config = json.loads(Path("railway.json").read_text())
    assert config["build"]["builder"] == "DOCKERFILE"
    assert config["deploy"]["preDeployCommand"] == "alembic upgrade head"
    assert config["deploy"]["healthcheckPath"] == "/health"


def test_dockerignore_keeps_secrets_and_local_data_out_of_the_image():
    ignored = Path(".dockerignore").read_text().splitlines()
    for entry in (".env", "*.db", ".venv", "snapshots"):
        assert entry in ignored


def test_aws_unit_runs_as_service_user_behind_nginx():
    unit = Path("deploy/aws/career-platform.service").read_text()
    assert "User=career-platform" in unit
    assert "EnvironmentFile=/etc/career-platform/env" in unit
    assert "WorkingDirectory=/opt/career-platform/app" in unit
    assert "--host 127.0.0.1 --port 8000 --workers 2" in unit
    assert "--proxy-headers --forwarded-allow-ips 127.0.0.1" in unit
    assert "After=network-online.target" in unit
    assert "ReadWritePaths=/var/lib/career-platform" in unit
    assert "Restart=on-failure" in unit
    assert "WantedBy=multi-user.target" in unit


def test_aws_nginx_serves_test_host_only_and_proxies_locally():
    config = Path("deploy/aws/nginx-career-platform.conf").read_text()
    assert "server_name aws.caelonk.me;" in config
    assert "listen 80 default_server;" in config
    assert "return 404;" in config
    assert "proxy_pass http://127.0.0.1:8000;" in config
    assert "proxy_set_header X-Forwarded-Proto $scheme;" in config
    assert "client_max_body_size 1m;" in config


def test_aws_env_example_lists_keys_without_values():
    lines = Path("deploy/aws/env.example").read_text().splitlines()
    keys = {line.split("=", 1)[0] for line in lines if line and not line.startswith("#")}
    assert keys == {"ENVIRONMENT", "DATABASE_URL", "SECRET_KEY", "ADMIN_PASSWORD", "SNAPSHOT_DIR"}
    text = "\n".join(lines)
    assert "sslmode=verify-full" in text
    assert "sslrootcert=/etc/ssl/certs/rds-global-bundle.pem" in text


def test_aws_caelonk_me_site_serves_https_and_redirects_http():
    # As installed on the EC2 instance at cutover, 2026-11-02 (plan Task 9).
    config = Path("deploy/aws/nginx-caelonk-me.conf").read_text()
    assert "server_name caelonk.me;" in config
    assert "listen 443 ssl;" in config
    assert "ssl_certificate /etc/letsencrypt/live/caelonk.me/fullchain.pem;" in config
    assert "return 301 https://$host$request_uri;" in config
    assert "proxy_pass http://127.0.0.1:8000;" in config
    assert "proxy_set_header X-Forwarded-Proto $scheme;" in config
