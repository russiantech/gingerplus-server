import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Uuid
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class UUIDMixin:
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)


class Entity(UUIDMixin, TimestampMixin):
    """UUID primary key + created/updated timestamps."""


def enum_col(enum_cls, **kw):
    """Portable string-backed enum column (no native PG enum => easy migrations)."""
    from sqlalchemy import Enum as SAEnum
    return SAEnum(enum_cls, native_enum=False, length=32, values_callable=lambda e: [m.value for m in e], validate_strings=True, **kw)
