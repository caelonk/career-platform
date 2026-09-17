from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.config import get_settings
from app.routes.admin import router as admin_router
from app.routes.auth import router as auth_router
from app.routes.public import router as public_router

BASE_DIR = Path(__file__).resolve().parent


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Career Platform",
        version="0.1.0",
        description="Personal career platform API foundation.",
    )
    app.state.settings = settings

    static_dir = BASE_DIR / "static"
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
    app.include_router(public_router)
    app.include_router(auth_router)
    app.include_router(admin_router)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/error/500", include_in_schema=False)
    async def error_500(request: Request):
        return templates.TemplateResponse(
            request,
            "errors/500.html",
            {"request": request, "detail": "An internal server error occurred."},
        )

    @app.exception_handler(500)
    async def internal_server_error(request: Request, exc: Exception):
        del exc
        return templates.TemplateResponse(
            request,
            "errors/500.html",
            {"request": request, "detail": "An internal server error occurred."},
        )

    return app
