import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, Entity, enum_col
from app.enums import ApplicationStatus, StoreStatus, StoreType


class Store(Entity, Base):
    """Physical store / distributor / dealer. Appears publicly only when approved AND is_public."""
    __tablename__ = "stores"

    name: Mapped[str] = mapped_column(String(200))
    slug: Mapped[str] = mapped_column(String(220), unique=True, index=True)
    store_type: Mapped[StoreType] = mapped_column(enum_col(StoreType), default=StoreType.STORE)
    status: Mapped[StoreStatus] = mapped_column(enum_col(StoreStatus), default=StoreStatus.PENDING, index=True)
    is_public: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    owner_user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("users.id", ondelete="SET NULL"))
    contact_person: Mapped[str | None] = mapped_column(String(150))
    phone: Mapped[str | None] = mapped_column(String(32))
    whatsapp: Mapped[str | None] = mapped_column(String(32))
    email: Mapped[str | None] = mapped_column(String(255))
    address: Mapped[str] = mapped_column(String(300))
    city: Mapped[str | None] = mapped_column(String(100))
    state: Mapped[str] = mapped_column(String(100), index=True)
    lga: Mapped[str | None] = mapped_column(String(100))
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    coverage_states: Mapped[list] = mapped_column(JSON, default=list)  # states this dealer can serve
    opening_hours: Mapped[str | None] = mapped_column(String(200))
    image_url: Mapped[str | None] = mapped_column(String(500))
    notes: Mapped[str | None] = mapped_column(Text)


class DistributorApplication(Entity, Base):
    __tablename__ = "distributor_applications"

    business_name: Mapped[str] = mapped_column(String(200))
    contact_person: Mapped[str] = mapped_column(String(150))
    phone: Mapped[str] = mapped_column(String(32))
    email: Mapped[str] = mapped_column(String(255), index=True)
    location: Mapped[str] = mapped_column(String(200))
    state: Mapped[str | None] = mapped_column(String(100))
    years_in_distribution: Mapped[int | None] = mapped_column(Integer)
    current_products: Mapped[str | None] = mapped_column(Text)
    expected_monthly_volume: Mapped[int | None] = mapped_column(Integer)
    motivation: Mapped[str | None] = mapped_column(Text)
    status: Mapped[ApplicationStatus] = mapped_column(enum_col(ApplicationStatus), default=ApplicationStatus.NEW, index=True)
    admin_notes: Mapped[str | None] = mapped_column(Text)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    store_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("stores.id", ondelete="SET NULL"))
