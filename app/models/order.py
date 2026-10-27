import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, Numeric, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, Entity, enum_col
from app.enums import AssignmentStatus, OrderChannel, OrderStatus, PaymentMethod, PaymentStatus


class Order(Entity, Base):
    __tablename__ = "orders"

    number: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("users.id", ondelete="SET NULL"), index=True)
    # contact snapshot (supports guest checkout)
    customer_name: Mapped[str] = mapped_column(String(200))
    customer_email: Mapped[str] = mapped_column(String(255), index=True)
    customer_phone: Mapped[str] = mapped_column(String(32))
    shipping_address: Mapped[dict] = mapped_column(JSON, default=dict)
    address_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("addresses.id", ondelete="SET NULL"))
    delivery_state: Mapped[str | None] = mapped_column(String(100), index=True)

    status: Mapped[OrderStatus] = mapped_column(enum_col(OrderStatus), default=OrderStatus.PENDING, index=True)
    payment_status: Mapped[PaymentStatus] = mapped_column(enum_col(PaymentStatus), default=PaymentStatus.UNPAID, index=True)
    payment_method: Mapped[PaymentMethod] = mapped_column(enum_col(PaymentMethod), default=PaymentMethod.PAYSTACK)
    channel: Mapped[OrderChannel] = mapped_column(enum_col(OrderChannel), default=OrderChannel.WEB, index=True)
    is_wholesale: Mapped[bool] = mapped_column(default=False)
    total_packs: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0)

    subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    discount_total: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    delivery_fee: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    total: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    currency: Mapped[str] = mapped_column(String(3), default="NGN")
    coupon_code: Mapped[str | None] = mapped_column(String(40))
    promotion_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("promotions.id", ondelete="SET NULL"))

    notes: Mapped[str | None] = mapped_column(Text)
    internal_notes: Mapped[str | None] = mapped_column(Text)
    tracking_note: Mapped[str | None] = mapped_column(String(500))
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Store / dealer fulfilment
    assigned_store_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("stores.id", ondelete="SET NULL"), index=True)
    suggested_store_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("stores.id", ondelete="SET NULL"))
    assignment_status: Mapped[AssignmentStatus] = mapped_column(enum_col(AssignmentStatus), default=AssignmentStatus.NONE)

    items: Mapped[list["OrderItem"]] = relationship(back_populates="order", cascade="all, delete-orphan", lazy="selectin")
    history: Mapped[list["OrderStatusHistory"]] = relationship(
        back_populates="order", cascade="all, delete-orphan", order_by="OrderStatusHistory.created_at", lazy="selectin"
    )
    payments: Mapped[list["Payment"]] = relationship(back_populates="order", lazy="selectin")  # noqa: F821
    assigned_store: Mapped["Store | None"] = relationship(foreign_keys=[assigned_store_id], lazy="joined")  # noqa: F821
    suggested_store: Mapped["Store | None"] = relationship(foreign_keys=[suggested_store_id], lazy="joined")  # noqa: F821


class OrderItem(Entity, Base):
    __tablename__ = "order_items"

    order_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("orders.id", ondelete="CASCADE"), index=True)
    product_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("products.id", ondelete="SET NULL"))
    variant_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("product_variants.id", ondelete="SET NULL"), index=True)
    product_name: Mapped[str] = mapped_column(String(200))
    variant_label: Mapped[str] = mapped_column(String(120))
    sku: Mapped[str] = mapped_column(String(64))
    image_url: Mapped[str | None] = mapped_column(String(500))
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    quantity: Mapped[int] = mapped_column(Integer)
    pack_equivalent: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=1)
    line_total: Mapped[Decimal] = mapped_column(Numeric(12, 2))

    order: Mapped[Order] = relationship(back_populates="items")


class OrderStatusHistory(Entity, Base):
    __tablename__ = "order_status_history"

    order_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("orders.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String(32))
    note: Mapped[str | None] = mapped_column(String(500))
    actor_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("users.id", ondelete="SET NULL"))
    is_public: Mapped[bool] = mapped_column(default=True)

    order: Mapped[Order] = relationship(back_populates="history")


class ShippingRate(Entity, Base):
    __tablename__ = "shipping_rates"

    state: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    fee: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    eta_min_days: Mapped[int] = mapped_column(Integer, default=2)
    eta_max_days: Mapped[int] = mapped_column(Integer, default=5)
    is_active: Mapped[bool] = mapped_column(default=True)
