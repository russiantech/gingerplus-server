import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, EmailStr, Field

from app.enums import PaymentProvider, PaymentPurpose, PaymentStatus
from app.schemas.common import ORM, Money


class DirectPaymentRequest(BaseModel):
    """Public 'pay now' page – pay an invoice / order number / any agreed amount."""
    name: str = Field(min_length=2)
    email: EmailStr
    phone: str | None = None
    amount: Decimal = Field(gt=0, le=Decimal("50000000"))
    order_number: str | None = None
    description: str | None = Field(default=None, max_length=255)


class InitPaymentResponse(BaseModel):
    reference: str
    authorization_url: str
    access_code: str | None = None
    amount: float


class PaymentOut(ORM):
    id: uuid.UUID
    reference: str
    purpose: PaymentPurpose
    provider: PaymentProvider
    status: PaymentStatus
    order_id: uuid.UUID | None
    email: EmailStr
    payer_name: str | None
    phone: str | None
    amount: Money
    currency: str
    description: str | None
    channel: str | None
    gateway_response: str | None
    paid_at: datetime | None
    admin_note: str | None
    created_at: datetime
    order_number: str | None = None


class PaymentPublicStatus(BaseModel):
    reference: str
    status: PaymentStatus
    amount: float
    order_number: str | None = None
    paid_at: datetime | None = None


class ManualConfirm(BaseModel):
    note: str | None = None
    reference: str | None = None


class ManualPaymentCreate(BaseModel):
    order_id: uuid.UUID
    amount: Decimal = Field(gt=0)
    note: str | None = None
    channel: str = "bank_transfer"
