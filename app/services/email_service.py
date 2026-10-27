"""Outbound email + in-app mailbox logging."""
import logging
import re
import uuid
from email.message import EmailMessage as MIMEMessage
from email.utils import formataddr, parseaddr

import aiosmtplib
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.templating import render_email
from app.enums import EmailDirection
from app.models import EmailMessage, User
from app.utils.text import normalize_email

log = logging.getLogger(__name__)


def _strip_html(html: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html)).strip()


async def _deliver(to: str, subject: str, html: str, text: str, reply_to: str | None = None) -> tuple[str, str | None]:
    if not settings.EMAIL_ENABLED:
        log.info("[email disabled] to=%s subject=%s", to, subject)
        return "skipped", None
    msg = MIMEMessage()
    name, addr = parseaddr(settings.EMAIL_FROM)
    msg["From"] = formataddr((name, addr))
    msg["To"] = to
    msg["Subject"] = subject
    if reply_to:
        msg["Reply-To"] = reply_to
    msg.set_content(text)
    msg.add_alternative(html, subtype="html")
    try:
        await aiosmtplib.send(
            msg, hostname=settings.SMTP_HOST, port=settings.SMTP_PORT,
            username=settings.SMTP_USER or None, password=settings.SMTP_PASSWORD or None,
            use_tls=settings.SMTP_TLS, start_tls=settings.SMTP_STARTTLS or None, timeout=15,
        )
        return "sent", None
    except Exception as exc:  # never break a business flow because mail failed
        log.exception("email delivery failed to %s", to)
        return "failed", str(exc)[:480]


async def send_email(
    db: AsyncSession | None,
    to: str,
    subject: str,
    template: str,
    *,
    log_to_inbox: bool = True,
    thread_id: uuid.UUID | None = None,
    contact_message_id: uuid.UUID | None = None,
    order_id: uuid.UUID | None = None,
    reply_to: str | None = None,
    is_system: bool = True,
    **ctx,
) -> EmailMessage | None:
    to = normalize_email(to)
    html = render_email(template, **ctx)
    text = ctx.get("body") or _strip_html(html)
    status, err = await _deliver(to, subject, html, text, reply_to)
    if not (db and log_to_inbox):
        return None
    user_id = (await db.execute(select(User.id).where(User.email == to))).scalar_one_or_none()
    _, from_addr = parseaddr(settings.EMAIL_FROM)
    rec = EmailMessage(
        thread_id=thread_id or uuid.uuid4(), direction=EmailDirection.OUTBOUND, from_email=from_addr, from_name="Southern Rose",
        to_email=to, subject=subject, body_text=text[:20000], body_html=html, is_read=True, is_system=is_system,
        send_status=status, send_error=err, user_id=user_id, contact_message_id=contact_message_id, order_id=order_id,
    )
    db.add(rec)
    await db.flush()
    return rec


async def notify_admin(db: AsyncSession | None, subject: str, body: str) -> None:
    await send_email(db, settings.ADMIN_NOTIFY_EMAIL, subject, "message.html", log_to_inbox=False, heading=subject, body=body)
