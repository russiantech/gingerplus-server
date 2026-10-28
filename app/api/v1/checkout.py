import uuid

from fastapi import APIRouter
from sqlalchemy import select

from app.api.deps import DB, CurrentUser, OptionalUser
from app.core.config import settings
from app.core.exceptions import AppError, NotFound
from app.enums import OrderStatus, PaymentStatus
from app.models import Order
from app.schemas.order import CheckoutRequest, CheckoutResponse, OrderOut, Quote, QuoteRequest, TrackRequest
from app.schemas.common import Message
from app.schemas.payment import InitPaymentResponse
from app.services import checkout_service, order_service, payment_service
from app.services.pricing_service import price_cart, to_quote
from app.services.settings_service import get_setting
from app.utils.text import normalize_email

router = APIRouter(tags=["checkout"])


def _public(order: Order) -> OrderOut:
    out = OrderOut.model_validate(order)
    out.history = [h for h in out.history if h.is_public]
    return out


@router.post("/checkout/quote", response_model=Quote)
async def quote(data: QuoteRequest, db: DB):
    contact = await get_setting(db, "contact")
    result = await price_cart(db, data.items, state=data.state, coupon_code=data.coupon_code)
    wa = (contact.get("whatsapp_numbers") or [settings.WHATSAPP_NUMBER])[0]
    return to_quote(result, wa)


@router.post("/checkout", response_model=CheckoutResponse, status_code=201)
async def checkout(data: CheckoutRequest, db: DB, user: OptionalUser):
    """Single endpoint for guests and customers. Returns the next step: pay_online | whatsapp | bank_transfer | retry_payment."""
    return await checkout_service.checkout(db, data, user)


@router.get("/orders/me", response_model=list[OrderOut])
async def my_orders(db: DB, user: CurrentUser):
    rows = (await db.execute(select(Order).where(Order.user_id == user.id).order_by(Order.created_at.desc()))).unique().scalars().all()
    return [_public(o) for o in rows]


@router.get("/orders/me/{order_id}", response_model=OrderOut)
async def my_order(order_id: uuid.UUID, db: DB, user: CurrentUser):
    o = await order_service.get_order(db, order_id)
    if o.user_id != user.id:
        raise NotFound("Order not found.")
    return _public(o)


@router.post("/orders/me/{order_id}/cancel", response_model=OrderOut)
async def cancel_my_order(order_id: uuid.UUID, db: DB, user: CurrentUser):
    o = await order_service.get_order(db, order_id)
    if o.user_id != user.id:
        raise NotFound("Order not found.")
    if o.status != OrderStatus.PENDING or o.payment_status == PaymentStatus.PAID:
        raise AppError("Only unpaid, unprocessed orders can be cancelled. Contact us for help.", code="cannot_cancel")
    await order_service.set_status(db, o, OrderStatus.CANCELLED, note="Cancelled by customer", actor=user)
    return _public(o)


@router.post("/orders/track", response_model=OrderOut)
async def track(data: TrackRequest, db: DB):
    o = await order_service.get_order_by_number(db, data.number)
    if not o or normalize_email(o.customer_email) != normalize_email(data.email):
        raise NotFound("We couldn't find an order with those details.", code="order_not_found")
    return _public(o)


@router.post("/orders/pay", response_model=InitPaymentResponse)
async def pay_order(data: TrackRequest, db: DB):
    """(Re)start online payment for an unpaid order (guest-friendly: order number + email)."""
    o = await order_service.get_order_by_number(db, data.number)
    if not o or normalize_email(o.customer_email) != normalize_email(data.email):
        raise NotFound("We couldn't find an order with those details.", code="order_not_found")
    p = await payment_service.init_for_order(db, o)
    return payment_service.init_response(p)
