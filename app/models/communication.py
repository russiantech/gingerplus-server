import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, Entity, enum_col
from app.enums import ContactStatus, ContactSubject, EmailDirection


class ContactMessage(Entity, Base):
    __tablename__ = "contact_messages"

    name: Mapped[str] = mapped_column(String(150))
    email: Mapped[str] = mapped_column(String(255), index=True)
    phone: Mapped[str | None] = mapped_column(String(32))
    subject: Mapped[ContactSubject] = mapped_column(enum_col(ContactSubject), default=ContactSubject.GENERAL)
    message: Mapped[str] = mapped_column(Text)
    extra: Mapped[dict] = mapped_column(JSON, default=dict)  # business name, location, volume ...
    status: Mapped[ContactStatus] = mapped_column(enum_col(ContactStatus), default=ContactStatus.NEW, index=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("users.id", ondelete="SET NULL"))
    email_thread_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    assigned_to_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("users.id", ondelete="SET NULL"))


class EmailMessage(Entity, Base):
    """In-app mailbox. user_id is set only when the address belongs to an existing user."""
    __tablename__ = "email_messages"

    thread_id: Mapped[uuid.UUID] = mapped_column(Uuid, index=True)
    direction: Mapped[EmailDirection] = mapped_column(enum_col(EmailDirection), index=True)
    from_email: Mapped[str] = mapped_column(String(255), index=True)
    from_name: Mapped[str | None] = mapped_column(String(200))
    to_email: Mapped[str] = mapped_column(String(255), index=True)
    subject: Mapped[str] = mapped_column(String(300))
    body_text: Mapped[str] = mapped_column(Text, default="")
    body_html: Mapped[str | None] = mapped_column(Text)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    is_starred: Mapped[bool] = mapped_column(Boolean, default=False)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False)  # auto-generated (verification codes excluded)
    send_status: Mapped[str | None] = mapped_column(String(20))  # sent | failed | skipped
    send_error: Mapped[str | None] = mapped_column(String(500))
    user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("users.id", ondelete="SET NULL"), index=True)
    contact_message_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("contact_messages.id", ondelete="SET NULL"))
    order_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("orders.id", ondelete="SET NULL"))


class NewsletterSubscriber(Entity, Base):
    __tablename__ = "newsletter_subscribers"

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    name: Mapped[str | None] = mapped_column(String(150))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    unsubscribe_token: Mapped[str] = mapped_column(String(64), unique=True)
    unsubscribed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
