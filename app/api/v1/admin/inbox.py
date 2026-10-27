import uuid

from fastapi import APIRouter, Depends, Header
from sqlalchemy import func, or_, select

from app.api.deps import DB, CurrentUser, require_permissions
from app.core.config import settings
from app.core.exceptions import NotFound, Unauthorized
from app.enums import ContactStatus, ContactSubject, EmailDirection, Permission as P
from app.models import ContactMessage, EmailMessage, NewsletterSubscriber, User
from app.schemas.common import Message, Page
from app.schemas.communication import ContactOut, ContactUpdate, EmailCompose, EmailFlags, EmailOut, InboundEmail, SubscriberOut
from app.services.email_service import send_email
from app.utils.pagination import PageParams, page_of, paginate
from app.utils.text import normalize_email

router = APIRouter(prefix="/admin", tags=["admin:inbox"])
emails_perm = Depends(require_permissions(P.EMAILS_MANAGE))
contacts_perm = Depends(require_permissions(P.CONTACTS_MANAGE))


async def _to_out(db, e: EmailMessage) -> EmailOut:
    o = EmailOut.model_validate(e)
    if e.user_id:
        u = await db.get(User, e.user_id)
        o.user_name = u.full_name if u else None
    return o


@router.get("/emails", response_model=Page[EmailOut], dependencies=[emails_perm])
async def list_emails(db: DB, params: PageParams = Depends(), folder: str = "inbox", q: str | None = None, unread: bool | None = None, customer_only: bool = False):
    stmt = select(EmailMessage).where(EmailMessage.is_archived.is_(folder == "archived"))
    if folder == "inbox":
        stmt = stmt.where(EmailMessage.direction == EmailDirection.INBOUND)
    elif folder == "sent":
        stmt = stmt.where(EmailMessage.direction == EmailDirection.OUTBOUND, EmailMessage.is_system.is_(False))
    elif folder == "system":
        stmt = stmt.where(EmailMessage.is_system.is_(True))
    elif folder == "starred":
        stmt = stmt.where(EmailMessage.is_starred.is_(True))
    if unread is not None:
        stmt = stmt.where(EmailMessage.is_read.is_(not unread))
    if customer_only:
        stmt = stmt.where(EmailMessage.user_id.is_not(None))
    if q:
        like = f"%{q}%"
        stmt = stmt.where(or_(EmailMessage.subject.ilike(like), EmailMessage.from_email.ilike(like), EmailMessage.to_email.ilike(like), EmailMessage.body_text.ilike(like)))
    rows, total, pages = await paginate(db, stmt.order_by(EmailMessage.created_at.desc()), params)
    return page_of([await _to_out(db, r) for r in rows], total, pages, params)


@router.get("/emails/unread-count", dependencies=[emails_perm])
async def unread_count(db: DB):
    n = (await db.execute(select(func.count()).select_from(EmailMessage).where(EmailMessage.direction == EmailDirection.INBOUND, EmailMessage.is_read.is_(False), EmailMessage.is_archived.is_(False)))).scalar_one()
    return {"unread": n}


@router.get("/emails/thread/{thread_id}", response_model=list[EmailOut], dependencies=[emails_perm])
async def thread(thread_id: uuid.UUID, db: DB):
    rows = (await db.execute(select(EmailMessage).where(EmailMessage.thread_id == thread_id).order_by(EmailMessage.created_at))).scalars().all()
    if not rows:
        raise NotFound("Thread not found.")
    for r in rows:
        if r.direction == EmailDirection.INBOUND:
            r.is_read = True
    return [await _to_out(db, r) for r in rows]


@router.post("/emails", response_model=EmailOut, status_code=201, dependencies=[emails_perm])
async def compose(data: EmailCompose, db: DB, actor: CurrentUser):
    """Send an email (or reply within a thread). Customers' replies land in the inbox via the inbound webhook."""
    rec = await send_email(db, data.to_email, data.subject, "message.html", thread_id=data.thread_id, contact_message_id=data.contact_message_id,
                           order_id=data.order_id, is_system=False, reply_to=settings.ADMIN_NOTIFY_EMAIL, body=data.body)
    if data.contact_message_id:
        c = await db.get(ContactMessage, data.contact_message_id)
        if c and c.status == ContactStatus.NEW:
            c.status = ContactStatus.IN_PROGRESS
    return await _to_out(db, rec)


@router.patch("/emails/{email_id}", response_model=EmailOut, dependencies=[emails_perm])
async def flag_email(email_id: uuid.UUID, data: EmailFlags, db: DB):
    e = await db.get(EmailMessage, email_id)
    if not e:
        raise NotFound("Email not found.")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(e, k, v)
    return await _to_out(db, e)


@router.post("/emails/inbound", response_model=Message, include_in_schema=True, tags=["webhooks"])
async def inbound_webhook(data: InboundEmail, db: DB, x_webhook_secret: str | None = Header(default=None)):
    """Provider webhook (Mailgun/Postmark/SendGrid route → map to this payload). Secured by shared secret."""
    if not x_webhook_secret or x_webhook_secret != settings.SECRET_KEY[:32]:
        raise Unauthorized("Invalid webhook secret")
    sender = normalize_email(data.from_email)
    user_id = (await db.execute(select(User.id).where(User.email == sender))).scalar_one_or_none()
    db.add(EmailMessage(thread_id=data.in_reply_to_thread or uuid.uuid4(), direction=EmailDirection.INBOUND, from_email=sender, from_name=data.from_name,
                        to_email=normalize_email(data.to_email), subject=data.subject, body_text=data.body_text, body_html=data.body_html, user_id=user_id))
    return Message(detail="stored")


# ---- contact form submissions ----
@router.get("/contacts", response_model=Page[ContactOut], dependencies=[contacts_perm])
async def list_contacts(db: DB, params: PageParams = Depends(), status: ContactStatus | None = None, subject: ContactSubject | None = None, q: str | None = None):
    stmt = select(ContactMessage)
    if status:
        stmt = stmt.where(ContactMessage.status == status)
    if subject:
        stmt = stmt.where(ContactMessage.subject == subject)
    if q:
        stmt = stmt.where(or_(ContactMessage.name.ilike(f"%{q}%"), ContactMessage.email.ilike(f"%{q}%"), ContactMessage.message.ilike(f"%{q}%")))
    rows, total, pages = await paginate(db, stmt.order_by(ContactMessage.created_at.desc()), params)
    return page_of(rows, total, pages, params)


@router.patch("/contacts/{cid}", response_model=ContactOut, dependencies=[contacts_perm])
async def update_contact(cid: uuid.UUID, data: ContactUpdate, db: DB):
    c = await db.get(ContactMessage, cid)
    if not c:
        raise NotFound("Message not found.")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(c, k, v)
    return c


# ---- newsletter ----
@router.get("/subscribers", response_model=Page[SubscriberOut], dependencies=[contacts_perm])
async def subscribers(db: DB, params: PageParams = Depends(), q: str | None = None):
    stmt = select(NewsletterSubscriber)
    if q:
        stmt = stmt.where(NewsletterSubscriber.email.ilike(f"%{q}%"))
    rows, total, pages = await paginate(db, stmt.order_by(NewsletterSubscriber.created_at.desc()), params)
    return page_of(rows, total, pages, params)


@router.delete("/subscribers/{sid}", response_model=Message, dependencies=[contacts_perm])
async def delete_subscriber(sid: uuid.UUID, db: DB):
    s = await db.get(NewsletterSubscriber, sid)
    if s:
        await db.delete(s)
    return Message(detail="Subscriber removed")
