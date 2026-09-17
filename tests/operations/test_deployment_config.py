from __future__ import annotations

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
