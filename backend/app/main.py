"""FastAPI application factory."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler

from .config import settings
from .db import init_db
from .ratelimit import limiter
from .routers import admin, play
from .routers import progress as progress_router
from .scheduler import shutdown_scheduler, start_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    if settings.scheduler_enabled:
        start_scheduler()
    try:
        yield
    finally:
        if settings.scheduler_enabled:
            shutdown_scheduler()


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
    return app


app = create_app()
