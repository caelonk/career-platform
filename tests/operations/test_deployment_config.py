from __future__ import annotations

import json
from pathlib import Path


def test_nginx_config_serves_snapshot_and_proxies_dynamic_requests():
    config = Path("deploy/nginx/career-platform.conf").read_text()
    assert "proxy_pass http://127.0.0.1:8000" in config
    assert "snapshot" in config
    assert "try_files" in config


def test_systemd_service_runs_uvicorn_without_root():
    unit = Path("deploy/systemd/career-platform.service").read_text()
    assert "User=career-platform" in unit
    assert "app.main:create_app" in unit
    assert "Restart=on-failure" in unit


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
