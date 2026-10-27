import uuid

from fastapi import APIRouter
from sqlalchemy import select

from app.api.deps import DB, OptionalUser
from app.core.config import settings
from app.enums import EmailDirection
from app.models import ContactMessage, EmailMessage, NewsletterSubscriber, User
from app.schemas.common import Message
from app.schemas.communication import ContactIn, NewsletterIn
from app.services.email_service import notify_admin, send_email
from app.utils.text import normalize_email, normalize_phone

router = APIRouter(tags=["contact"])


@router.post("/contact", response_model=Message, status_code=201)
async def submit_contact(data: ContactIn, db: DB, user: OptionalUser):
    """Contact form. Creates a ContactMessage + an inbound in-app email (linked to a user only if the address already belongs to one)."""
    if data.website:  # honeypot
        return Message(detail="Thanks! We'll get back to you shortly.")
    email = normalize_email(data.email)
    owner = user or (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
    thread = uuid.uuid4()
    msg = ContactMessage(name=data.name, email=email, phone=normalize_phone(data.phone), subject=data.subject, message=data.message,
                         extra=data.extra, user_id=owner.id if owner else None, email_thread_id=thread)
    db.add(msg)
    await db.flush()
    subject = f"[{data.subject.value.title()}] Message from {data.name}"
    db.add(EmailMessage(thread_id=thread, direction=EmailDirection.INBOUND, from_email=email, from_name=data.name, to_email=settings.ADMIN_NOTIFY_EMAIL,
                        subject=subject, body_text=data.message + ("\n\n" + "\n".join(f"{k}: {v}" for k, v in data.extra.items()) if data.extra else ""),
                        is_read=False, user_id=owner.id if owner else None, contact_message_id=msg.id))
    await send_email(db, email, "We got your message — Southern Rose", "message.html", log_to_inbox=False, heading="Thanks for reaching out",
                     body=f"Hi {data.name},\n\nWe've received your message and will respond within 24 hours. For faster help, WhatsApp us on +234 802 772 4193.\n\n— Southern Rose Team")
    await notify_admin(db, subject, f"{data.name} <{email}> {data.phone or ''}\n\n{data.message}")
    return Message(detail="Thanks! We'll get back to you within 24 hours.")


@router.post("/newsletter/subscribe", response_model=Message, status_code=201)
async def subscribe(data: NewsletterIn, db: DB):
    email = normalize_email(data.email)
    sub = (await db.execute(select(NewsletterSubscriber).where(NewsletterSubscriber.email == email))).scalar_one_or_none()
    if sub:
        sub.is_active, sub.unsubscribed_at = True, None
    else:
        db.add(NewsletterSubscriber(email=email, name=data.name, unsubscribe_token=uuid.uuid4().hex))
        await send_email(db, email, "You're on the list — Southern Rose", "message.html", log_to_inbox=False, heading="Stay in the loop",
                         body="Thanks for subscribing! You'll be first to know about new products, recipes and wholesale offers.")
    return Message(detail="You're subscribed. Welcome to Southern Rose!")


@router.get("/newsletter/unsubscribe", response_model=Message)
async def unsubscribe(token: str, db: DB):
    from datetime import datetime, timezone
    sub = (await db.execute(select(NewsletterSubscriber).where(NewsletterSubscriber.unsubscribe_token == token))).scalar_one_or_none()
    if sub:
        sub.is_active, sub.unsubscribed_at = False, datetime.now(timezone.utc)
    return Message(detail="You've been unsubscribed.")
