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
        await get_redis().ping()
    except Exception:  # pragma: no cover
        log.warning("Redis is not reachable — registration & sessions will fail until it is up.")
    Path(settings.UPLOAD_DIR).mkdir(parents=True, exist_ok=True)
    yield
    await close_redis()


def create_app() -> FastAPI:
    app = FastAPI(title=settings.APP_NAME, version="1.0.0", lifespan=lifespan,
                  docs_url=None if settings.is_production else "/docs", redoc_url=None, openapi_url=f"{settings.API_V1_PREFIX}/openapi.json")
    app.add_middleware(CORSMiddleware, allow_origins=settings.CORS_ORIGINS, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
    register_exception_handlers(app)

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        resp = await call_next(request)
        resp.headers.setdefault("X-Content-Type-Options", "nosniff")
        resp.headers.setdefault("X-Frame-Options", "DENY")
        resp.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        return resp

    @app.get("/health", tags=["system"])
    async def health():
        return {"status": "ok", "service": settings.APP_NAME}

    app.include_router(api_router, prefix=settings.API_V1_PREFIX)
    static_dir = Path(__file__).parent / "static"
    static_dir.mkdir(exist_ok=True)
    Path(settings.UPLOAD_DIR).mkdir(parents=True, exist_ok=True)
    app.mount("/static", StaticFiles(directory=static_dir), name="static")
    return app


app = create_app()
