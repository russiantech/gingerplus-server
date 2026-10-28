"""Vercel serverless entrypoint (Python runtime). All routes are rewritten here by vercel.json."""
from app.main import app  # noqa: F401
