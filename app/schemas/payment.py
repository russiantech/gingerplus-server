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
    """Everything the browser needs to open the provider's in-page popup. Secrets never appear here (public key only)."""
    reference: str
    provider: str  # paystack | flutterwave | mock
    authorization_url: str | None = None  # last-resort fallback if the popup script cannot load
    access_code: str | None = None
    public_key: str | None = None
    mock: bool = False
    amount: float
    currency: str = "NGN"
    email: str | None = None
    name: str | None = None
    phone: str | None = None
    description: str | None = None


class VerifyRequest(BaseModel):
    reference: str


class MockCompleteRequest(BaseModel):
    reference: str
    outcome: str = "success"  # success | failed


class OnlineConfig(BaseModel):
    available: bool
    provider: str | None = None
    mock: bool = False


class BankDetails(BaseModel):
    bank_name: str = ""
    account_name: str = ""
    account_number: str = ""
    instructions: str = ""


class PaymentConfigOut(BaseModel):
    online: OnlineConfig
    bank_transfer: BankDetails | None = None


class ProviderUpdate(BaseModel):
    display_name: str | None = None
    is_enabled: bool | None = None
    mode: str | None = None
    public_key: str | None = None
    secret_key: str | None = None  # write-only; blank/omitted = keep the stored secret
    clear_secret: bool = False
    webhook_secret: str | None = None
    clear_webhook_secret: bool = False
    extra: dict[str, str] | None = None


class ProviderOut(BaseModel):
    provider: str
    display_name: str
    kind: str
    blurb: str
    is_enabled: bool
    is_default: bool
    mode: str
    public_key: str | None = None
    has_secret: bool
    secret_masked: str | None = None
    secret_fingerprint: str | None = None
    has_webhook_secret: bool
    needs_reentry: bool = False
    extra: dict = {}
    env_available: bool
    source: str  # database | environment | none
    active: bool
    webhook_url: str | None = None
    updated_at: datetime | None = None


class TestResult(BaseModel):
    ok: bool
    message: str
    source: str


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
    message: str | None = None


class ManualConfirm(BaseModel):
    note: str | None = None
    reference: str | None = None


class ManualPaymentCreate(BaseModel):
    order_id: uuid.UUID
    amount: Decimal = Field(gt=0)
    note: str | None = None
    channel: str = "bank_transfer"
