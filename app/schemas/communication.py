import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from app.enums import ContactStatus, ContactSubject, EmailDirection
from app.schemas.common import ORM


class ContactIn(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    email: EmailStr
    phone: str | None = Field(default=None, max_length=32)
    subject: ContactSubject = ContactSubject.GENERAL
    message: str = Field(min_length=5, max_length=5000)
    extra: dict = {}
    website: str | None = None  # honeypot – must stay empty


class ContactOut(ORM):
    id: uuid.UUID
    name: str
    email: EmailStr
    phone: str | None
    subject: ContactSubject
    message: str
    extra: dict
    status: ContactStatus
    user_id: uuid.UUID | None
    email_thread_id: uuid.UUID | None
    created_at: datetime


class ContactUpdate(BaseModel):
    status: ContactStatus | None = None
    assigned_to_id: uuid.UUID | None = None


class EmailOut(ORM):
    id: uuid.UUID
    thread_id: uuid.UUID
    direction: EmailDirection
    from_email: str
    from_name: str | None
    to_email: str
    subject: str
    body_text: str
    body_html: str | None
    is_read: bool
    is_starred: bool
    is_archived: bool
    is_system: bool
    send_status: str | None
    send_error: str | None
    user_id: uuid.UUID | None
    user_name: str | None = None
    contact_message_id: uuid.UUID | None
    order_id: uuid.UUID | None
    created_at: datetime


class EmailCompose(BaseModel):
    to_email: EmailStr
    subject: str = Field(min_length=1, max_length=300)
    body: str = Field(min_length=1)
    thread_id: uuid.UUID | None = None
    contact_message_id: uuid.UUID | None = None
    order_id: uuid.UUID | None = None


class EmailFlags(BaseModel):
    is_read: bool | None = None
    is_starred: bool | None = None
    is_archived: bool | None = None


class InboundEmail(BaseModel):
    """Webhook payload (Mailgun/Sendgrid/Postmark adapters map into this)."""
    from_email: EmailStr
    from_name: str | None = None
    to_email: EmailStr
    subject: str = "(no subject)"
    body_text: str = ""
    body_html: str | None = None
    in_reply_to_thread: uuid.UUID | None = None


class NewsletterIn(BaseModel):
    email: EmailStr
    name: str | None = None


class SubscriberOut(ORM):
    id: uuid.UUID
    email: EmailStr
    name: str | None
    is_active: bool
    created_at: datetime
