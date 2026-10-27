import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, EmailStr, Field

from app.enums import (AssignmentStatus, OrderChannel, OrderStatus, PaymentMethod, PaymentStatus)
from app.schemas.common import ORM, Money
from app.schemas.user import AddressIn


class CartLine(BaseModel):
    variant_id: uuid.UUID
    quantity: int = Field(ge=1, le=10000)


class QuoteRequest(BaseModel):
    items: list[CartLine] = Field(min_length=1)
    state: str | None = None
    coupon_code: str | None = None


class QuoteLine(BaseModel):
    variant_id: uuid.UUID
    product_name: str
    variant_label: str
    image_url: str | None
    quantity: int
    base_unit_price: float
    unit_price: float
    line_total: float
    tier_label: str | None = None
    promo_label: str | None = None
    available: bool = True


class Quote(BaseModel):
    lines: list[QuoteLine]
    subtotal: float
    discount_total: float
    delivery_fee: float
    total: float
    total_packs: float
    coupon_code: str | None = None
    coupon_error: str | None = None
    promotion_name: str | None = None
    is_wholesale: bool
    online_payment_allowed: bool
    online_payment_max_packs: int
    whatsapp_url: str | None = None
    eta_min_days: int | None = None
    eta_max_days: int | None = None


class CheckoutRequest(BaseModel):
    items: list[CartLine] = Field(min_length=1)
    # contact (required for guests; prefilled from account otherwise)
    name: str | None = None
    email: EmailStr | None = None
    phone: str | None = None
    address_id: uuid.UUID | None = None          # existing saved address
    address: AddressIn | None = None             # or a new one
    save_address: bool = False
    coupon_code: str | None = None
    notes: str | None = None
    payment_method: PaymentMethod = PaymentMethod.PAYSTACK
    channel: OrderChannel = OrderChannel.WEB
    preferred_store_id: uuid.UUID | None = None
    request_store_match: bool = False            # let the system suggest the nearest store (admin approves)


class OrderItemOut(ORM):
    id: uuid.UUID
    variant_id: uuid.UUID | None
    product_name: str
    variant_label: str
    sku: str
    image_url: str | None
    unit_price: Money
    quantity: int
    line_total: Money


class StatusEvent(ORM):
    status: str
    note: str | None
    is_public: bool
    created_at: datetime


class StoreBrief(ORM):
    id: uuid.UUID
    name: str
    store_type: str
    phone: str | None
    whatsapp: str | None
    address: str
    city: str | None
    state: str


class OrderOut(ORM):
    id: uuid.UUID
    number: str
    status: OrderStatus
    payment_status: PaymentStatus
    payment_method: PaymentMethod
    channel: OrderChannel
    is_wholesale: bool
    total_packs: Money
    customer_name: str
    customer_email: EmailStr
    customer_phone: str
    shipping_address: dict
    delivery_state: str | None
    subtotal: Money
    discount_total: Money
    delivery_fee: Money
    total: Money
    currency: str
    coupon_code: str | None
    notes: str | None
    tracking_note: str | None
    paid_at: datetime | None
    created_at: datetime
    items: list[OrderItemOut]
    history: list[StatusEvent] = []
    assigned_store: StoreBrief | None = None


class AdminOrderOut(OrderOut):
    user_id: uuid.UUID | None
    internal_notes: str | None
    assignment_status: AssignmentStatus
    suggested_store: StoreBrief | None = None
    assigned_store_id: uuid.UUID | None
    suggested_store_id: uuid.UUID | None


class CheckoutResponse(BaseModel):
    order: OrderOut
    authorization_url: str | None = None
    payment_reference: str | None = None
    whatsapp_url: str | None = None
    next_step: str  # pay_online | whatsapp | bank_transfer | confirmation


class TrackRequest(BaseModel):
    number: str
    email: EmailStr


class AdminOrderCreate(CheckoutRequest):
    user_id: uuid.UUID | None = None
    mark_paid: bool = False
    delivery_fee_override: Decimal | None = None


class OrderStatusUpdate(BaseModel):
    status: OrderStatus
    note: str | None = None
    notify_customer: bool = True
    is_public: bool = True


class OrderUpdate(BaseModel):
    internal_notes: str | None = None
    tracking_note: str | None = None
    delivery_fee: Decimal | None = None


class StoreAssign(BaseModel):
    store_id: uuid.UUID | None = None


class ShippingRateIn(BaseModel):
    state: str
    fee: Decimal = Field(ge=0)
    eta_min_days: int = 2
    eta_max_days: int = 5
    is_active: bool = True


class ShippingRateOut(ORM):
    id: uuid.UUID
    state: str
    fee: Money
    eta_min_days: int
    eta_max_days: int
    is_active: bool
