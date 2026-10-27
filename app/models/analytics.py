import uuid

from sqlalchemy import Boolean, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, Entity


class PageView(Entity, Base):
    __tablename__ = "page_views"

    session_id: Mapped[str] = mapped_column(String(64), index=True)
    path: Mapped[str] = mapped_column(String(500), index=True)
    referrer: Mapped[str | None] = mapped_column(String(500))
    referrer_host: Mapped[str | None] = mapped_column(String(200), index=True)
    utm_source: Mapped[str | None] = mapped_column(String(100))
    device: Mapped[str | None] = mapped_column(String(20))
    browser: Mapped[str | None] = mapped_column(String(60))
    os: Mapped[str | None] = mapped_column(String(60))
    is_bot: Mapped[bool] = mapped_column(Boolean, default=False)
    user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("users.id", ondelete="SET NULL"))
