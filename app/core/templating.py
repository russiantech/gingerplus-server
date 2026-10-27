from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.core.config import settings

_env = Environment(
    loader=FileSystemLoader(Path(__file__).resolve().parent.parent / "templates" / "emails"),
    autoescape=select_autoescape(["html"]),
)


def render_email(template: str, **ctx) -> str:
    ctx.setdefault("site_url", settings.SITE_URL)
    ctx.setdefault("year", datetime.now().year)
    return _env.get_template(template).render(**ctx)
