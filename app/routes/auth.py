from __future__ import annotations

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path

from app.config import get_settings
from app.services.auth import clear_admin_cookie, verify_password, write_admin_cookie

router = APIRouter()
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parents[1] / "templates"))


def _is_valid_login(username: str, password: str) -> bool:
    if username != "admin":
        return False
    expected = get_settings().admin_password
    return bool(expected) and verify_password(password, expected)


@router.get("/auth/login")
async def login_form(request: Request, error: str | None = None):
    return templates.TemplateResponse(request, "auth/login.html", {"request": request, "error": error})


@router.post("/auth/login")
async def login_submit(request: Request, username: str = Form(...), password: str = Form(...)):
    if not _is_valid_login(username, password):
        response = RedirectResponse(url="/auth/login?error=invalid", status_code=303)
        return response
    response = RedirectResponse(url="/admin", status_code=303)
    write_admin_cookie(response, "admin")
    return response


@router.post("/auth/logout")
async def logout():
    response = RedirectResponse(url="/auth/login", status_code=303)
    clear_admin_cookie(response)
    return response
