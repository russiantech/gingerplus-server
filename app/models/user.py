import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, Entity, enum_col
from app.enums import UserType


class Role(Entity, Base):
    __tablename__ = "roles"

    key: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str] = mapped_column(String(255), default="")
    permissions: Mapped[list] = mapped_column(JSON, default=list)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False)


class User(Entity, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    first_name: Mapped[str] = mapped_column(String(100))
    last_name: Mapped[str] = mapped_column(String(100), default="")
    phone: Mapped[str | None] = mapped_column(String(32), index=True)
    avatar_url: Mapped[str | None] = mapped_column(String(500))
    user_type: Mapped[UserType] = mapped_column(enum_col(UserType), default=UserType.CUSTOMER, index=True)
    role_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("roles.id", ondelete="SET NULL"), index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    email_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    marketing_opt_in: Mapped[bool] = mapped_column(Boolean, default=False)
    # Customer <-> store link (admin managed, or system suggestion approved by admin)
    linked_store_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("stores.id", ondelete="SET NULL", use_alter=True, name="fk_users_linked_store"))
    notes: Mapped[str | None] = mapped_column(Text)

    role: Mapped[Role | None] = relationship(lazy="joined")
    addresses: Mapped[list["Address"]] = relationship(back_populates="user", cascade="all, delete-orphan")  # noqa: F821

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def permissions(self) -> list[str]:
        return list(self.role.permissions) if self.role else []

    @property
    def role_key(self) -> str | None:
        return self.role.key if self.role else None
