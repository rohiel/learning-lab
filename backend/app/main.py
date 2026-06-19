"""FastAPI application factory.

In production a single container serves both the JSON API (/api/*) and the built
React SPA (/). Serving same-origin means no CORS and the shared secret is
injected into the page at runtime from the server env (no rebuild to rotate it).
"""
import json
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler
from sqlalchemy import select

from .config import settings
from .db import SessionLocal, init_db
from .models import Student
from .ratelimit import limiter
from .routers import admin, play
from .routers import progress as progress_router
from .scheduler import shutdown_scheduler, start_scheduler


def inject_app_config(html: str, api_base: str, api_secret: str) -> str:
    """Inject runtime config into the SPA's <head>."""
    cfg = json.dumps({"apiBase": api_base, "apiSecret": api_secret})
    return html.replace("</head>", f"<script>window.__APP_CONFIG__ = {cfg};</script></head>", 1)


def _auto_seed_student() -> None:
    if not settings.auto_seed_student:
        return
    db = SessionLocal()
    try:
        if not db.scalar(select(Student)):
            db.add(Student(name=settings.default_student_name, current_week=1, current_day=1))
            db.commit()
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    _auto_seed_student()
    if settings.scheduler_enabled:
        start_scheduler()
    try:
        yield
    finally:
        if settings.scheduler_enabled:
            shutdown_scheduler()


def _mount_spa(app: FastAPI) -> None:
    static_dir = settings.static_dir
    if not static_dir or not os.path.isdir(static_dir):
        return  # dev: no build present -> API only (Vite serves the frontend)

    assets_dir = os.path.join(static_dir, "assets")
    if os.path.isdir(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    index_path = os.path.join(static_dir, "index.html")

    @app.get("/", include_in_schema=False)
    async def spa_root():
        try:
            with open(index_path, encoding="utf-8") as f:
                html = f.read()
        except OSError:
            return HTMLResponse("<h1>Frontend not built</h1>", status_code=500)
        return HTMLResponse(inject_app_config(html, settings.spa_api_base, settings.api_shared_secret))


def create_app() -> FastAPI:
    app = FastAPI(title="Anam's Learning Lab API", version="0.1.0", lifespan=lifespan)

    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(admin.router, prefix="/api")
    app.include_router(play.router, prefix="/api")
    app.include_router(progress_router.router, prefix="/api")
    _mount_spa(app)
    return app


app = create_app()
