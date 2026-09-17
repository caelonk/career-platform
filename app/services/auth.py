from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
from datetime import datetime, timedelta
from typing import Any

from fastapi import HTTPException, Request

from app.config import get_settings

_COOKIE_NAME = "career_platform_admin"


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 200_000)
    return f"pbkdf2_sha256${200_000}${base64.b64encode(salt).decode()}${base64.b64encode(digest).decode()}"


def verify_password(password: str, hashed_password: str) -> bool:
    if not hashed_password.startswith("pbkdf2_sha256$"):
        return False
    _, iterations, salt_b64, digest_b64 = hashed_password.split("$")
    salt = base64.b64decode(salt_b64.encode())
    expected = base64.b64decode(digest_b64.encode())
    actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, int(iterations))
    return hmac.compare_digest(actual, expected)


def _sign_payload(payload: str) -> str:
    secret = get_settings().secret_key.encode("utf-8")
    digest = hmac.new(secret, payload.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{payload}.{digest}"


def _verify_signed_payload(raw: str) -> dict[str, Any] | None:
    if "." not in raw:
        return None
    payload, digest = raw.rsplit(".", 1)
    expected = hmac.new(get_settings().secret_key.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(digest, expected):
        return None
    try:
        return json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)).decode("utf-8"))
    except Exception:
        return None


def _encode_payload(data: dict[str, Any]) -> str:
    encoded = json.dumps(data, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(encoded).decode("utf-8").rstrip("=")


def is_admin_authenticated(request: Request) -> bool:
    token = request.cookies.get(_COOKIE_NAME)
    if not token:
        return False
    payload = _verify_signed_payload(token)
    if not payload:
        return False
    expires_at = payload.get("expires_at")
    if expires_at and datetime.fromisoformat(expires_at) < datetime.utcnow():
        return False
    return payload.get("user") == "admin"


def require_admin(request: Request):
    if not is_admin_authenticated(request):
        raise HTTPException(status_code=303, headers={"Location": "/auth/login"})
    return {"user": "admin"}


def write_admin_cookie(response, user: str = "admin") -> None:
    expiration = (datetime.utcnow() + timedelta(hours=12)).isoformat()
    payload = {"user": user, "expires_at": expiration}
    token = _sign_payload(_encode_payload(payload))
    response.set_cookie(
        key=_COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        secure=get_settings().environment == "production",
        max_age=60 * 60 * 12,
    )


def clear_admin_cookie(response) -> None:
    response.delete_cookie(_COOKIE_NAME)
