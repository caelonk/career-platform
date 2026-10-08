from __future__ import annotations

from sqlalchemy.engine import make_url

from app.config import normalize_database_url

LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}


def require_local_test_database(url: str) -> str:
    """Postgres tests drop the public schema, so they may only touch a local throwaway database."""
    normalized = normalize_database_url(url)
    if make_url(normalized).host not in LOCAL_HOSTS:
        raise ValueError("TEST_POSTGRES_URL must point at a local throwaway database (localhost); these tests wipe it.")
    return normalized
