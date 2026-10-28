import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import JSON, DateTime, ForeignKey, Numeric, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, Entity, enum_col
from app.enums import PaymentProvider, PaymentPurpose, PaymentStatus


class Payment(Entity, Base):
    __tablename__ = "payments"

    reference: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    purpose: Mapped[PaymentPurpose] = mapped_column(enum_col(PaymentPurpose), default=PaymentPurpose.ORDER)
    provider: Mapped[PaymentProvider] = mapped_column(enum_col(PaymentProvider), default=PaymentProvider.PAYSTACK)
    status: Mapped[PaymentStatus] = mapped_column(enum_col(PaymentStatus), default=PaymentStatus.PENDING, index=True)
    order_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("orders.id", ondelete="SET NULL"), index=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("users.id", ondelete="SET NULL"), index=True)
    email: Mapped[str] = mapped_column(String(255), index=True)
    payer_name: Mapped[str | None] = mapped_column(String(200))
    phone: Mapped[str | None] = mapped_column(String(32))
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    currency: Mapped[str] = mapped_column(String(3), default="NGN")
    description: Mapped[str | None] = mapped_column(String(255))
    channel: Mapped[str | None] = mapped_column(String(40))  # card, bank, ussd ...
    authorization_url: Mapped[str | None] = mapped_column(String(500))
    access_code: Mapped[str | None] = mapped_column(String(100))
    gateway_response: Mapped[str | None] = mapped_column(String(255))
    gateway_payload: Mapped[dict] = mapped_column(JSON, default=dict)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    confirmed_by_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("users.id", ondelete="SET NULL"))
    admin_note: Mapped[str | None] = mapped_column(Text)

    order: Mapped["Order | None"] = relationship(back_populates="payments")  # noqa: F821


class PaymentProviderConfig(Entity, Base):
    """Admin-managed gateway credentials / bank details. Secrets are stored encrypted (see app.core.crypto)."""
    __tablename__ = "payment_providers"

    provider: Mapped[str] = mapped_column(String(32), unique=True, index=True)  # paystack | flutterwave | bank_transfer
    display_name: Mapped[str | None] = mapped_column(String(80))
    is_enabled: Mapped[bool] = mapped_column(default=False)
    is_default: Mapped[bool] = mapped_column(default=False)
    mode: Mapped[str] = mapped_column(String(8), default="test")  # test | live
    public_key: Mapped[str | None] = mapped_column(String(255))
    secret_key_enc: Mapped[str | None] = mapped_column(Text)
    webhook_secret_enc: Mapped[str | None] = mapped_column(Text)
    secret_fingerprint: Mapped[str | None] = mapped_column(String(32))  # SHA-256 prefix, display/change-detection only
    extra: Mapped[dict] = mapped_column(JSON, default=dict)  # e.g. bank_name / account_number / instructions
    updated_by_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("users.id", ondelete="SET NULL"))
