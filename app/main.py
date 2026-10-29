import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.router import api_router
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import setup_logging
from app.core.redis import close_redis, get_redis

log = logging.getLogger("app")


@asynccontextmanager
async def lifespan(_: FastAPI):
    setup_logging(settings.DEBUG)
    try:
        if not await get_redis().ping():
            log.warning("Redis is not reachable — using the in-memory fallback (single instance only).")
    except Exception:  # pragma: no cover
        log.warning("Redis check failed — using the in-memory fallback.")
    if settings.AUTO_SEED:
        try:
            from app.db.init_db import seed_all
            await seed_all()
        except Exception:  # never block startup on seeding
            log.exception("Auto-seed failed (continuing)")
    yield
    await close_redis()


class TrailingSlashMiddleware:
    """Some hosts (Vercel) forward `/api/v1/catalog/products/`. Treat `/x/` and `/x` as the same route instead of 404-ing."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] in ("http", "websocket"):
            path = scope.get("path", "")
            if len(path) > 1 and path.endswith("/"):
                scope = dict(scope)
                scope["path"] = path.rstrip("/") or "/"
                if scope.get("raw_path"):
                    scope["raw_path"] = scope["raw_path"].rstrip(b"/") or b"/"
        await self.app(scope, receive, send)


def create_app() -> FastAPI:
    app = FastAPI(title=settings.APP_NAME, version="1.0.0", lifespan=lifespan,
                  docs_url=None if settings.is_production else "/docs", redoc_url=None, openapi_url=f"{settings.API_V1_PREFIX}/openapi.json")
    app.add_middleware(CORSMiddleware, allow_origins=settings.CORS_ORIGINS, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
    app.add_middleware(TrailingSlashMiddleware)
    register_exception_handlers(app)

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        try:
            resp = await call_next(request)
        except Exception:  # returned inside CORS middleware so browsers still see a readable JSON error
            log.exception("Unhandled error on %s %s", request.method, request.url.path)
            resp = JSONResponse(status_code=500, content={"detail": "Something went wrong on our side. Please try again.", "code": "server_error"})
        resp.headers.setdefault("X-Content-Type-Options", "nosniff")
        resp.headers.setdefault("X-Frame-Options", "DENY")
        resp.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        return resp

    @app.get("/health", tags=["system"])
    async def health():
        return {"status": "ok", "service": settings.APP_NAME}

    app.include_router(api_router, prefix=settings.API_V1_PREFIX)
    static_dir = Path(__file__).parent / "static"
    try:  # read-only filesystems (Vercel/Lambda) can't create directories — that must not stop the app
        static_dir.mkdir(exist_ok=True)
        Path(settings.UPLOAD_DIR).mkdir(parents=True, exist_ok=True)
    except OSError:
        log.warning("Filesystem is read-only; local uploads disabled (configure STORAGE_BACKEND).")
    if static_dir.is_dir():
        app.mount("/static", StaticFiles(directory=static_dir), name="static")
    return app


app = create_app()
