"""Vercel entrypoint (zero-config FastAPI): Vercel serves every route through this ASGI `app`.

Deploy with the Vercel project's *Root Directory* set to `server`. Locally use: uvicorn app.main:app
"""
from app.main import app  # noqa: F401
