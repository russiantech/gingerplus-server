import logging
import secrets
import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import AppError, NotFound, PaymentError
from app.enums import OrderStatus, PaymentProvider, PaymentPurpose, PaymentStatus
from app.models import Order, Payment, User
from app.schemas.payment import DirectPaymentRequest
from app.services import order_service, paystack_service
from app.services.email_service import notify_admin, send_email
from app.utils.text import normalize_email, normalize_phone

log = logging.getLogger(__name__)


def new_reference(prefix: str = "SR") -> str:
    return f"{prefix}-{datetime.now(timezone.utc):%y%m%d%H%M%S}-{secrets.token_hex(4).upper()}"


def _callback() -> str:
    return settings.SITE_URL.rstrip("/") + settings.PAYSTACK_CALLBACK_PATH


async def _init_gateway(db: AsyncSession, payment: Payment, metadata: dict) -> Payment:
    data = await paystack_service.initialize(email=payment.email, amount=payment.amount, reference=payment.reference,
                                             callback_url=_callback(), metadata=metadata)
    payment.authorization_url = data["authorization_url"]
    payment.access_code = data.get("access_code")
    await db.flush()
    return payment


async def init_for_order(db: AsyncSession, order: Order, user: User | None = None) -> Payment:
    if order.payment_status == PaymentStatus.PAID:
        raise AppError("This order is already paid.", code="already_paid")
    if order.status in (OrderStatus.CANCELLED, OrderStatus.REFUNDED):
        raise AppError("This order is no longer payable.", code="order_closed")
    paid = await paid_total(db, order.id)
    due = Decimal(order.total) - paid
    p = Payment(reference=new_reference(), purpose=PaymentPurpose.ORDER, provider=PaymentProvider.PAYSTACK, status=PaymentStatus.PENDING,
                order_id=order.id, user_id=order.user_id, email=order.customer_email, payer_name=order.customer_name,
                phone=order.customer_phone, amount=due, description=f"Order {order.number}")
    db.add(p)
    await db.flush()
    order.payment_status = PaymentStatus.PENDING
    return await _init_gateway(db, p, {"order_id": str(order.id), "order_number": order.number, "purpose": "order"})


async def init_direct(db: AsyncSession, data: DirectPaymentRequest, user: User | None) -> Payment:
    order = None
    if data.order_number:
        order = await order_service.get_order_by_number(db, data.order_number)
        if not order or normalize_email(order.customer_email) != normalize_email(data.email):
            raise NotFound("We couldn't match that order number to this email.", code="order_mismatch")
        if order.payment_status == PaymentStatus.PAID:
            raise AppError("This order is already paid.", code="already_paid")
    p = Payment(reference=new_reference("SRD"), purpose=PaymentPurpose.ORDER if order else PaymentPurpose.DIRECT,
                provider=PaymentProvider.PAYSTACK, status=PaymentStatus.PENDING, order_id=order.id if order else None,
                user_id=user.id if user else (order.user_id if order else None), email=normalize_email(data.email), payer_name=data.name,
                phone=normalize_phone(data.phone), amount=data.amount,
                description=data.description or (f"Payment for order {order.number}" if order else "Direct payment"))
    db.add(p)
    await db.flush()
    return await _init_gateway(db, p, {"purpose": p.purpose.value, "order_number": order.number if order else None, "payer": data.name})


async def paid_total(db: AsyncSession, order_id: uuid.UUID) -> Decimal:
    v = (await db.execute(select(func.coalesce(func.sum(Payment.amount), 0)).where(Payment.order_id == order_id, Payment.status == PaymentStatus.PAID))).scalar_one()
    return Decimal(v)


async def get_by_reference(db: AsyncSession, reference: str, lock: bool = False) -> Payment | None:
    q = select(Payment).where(Payment.reference == reference)
    if lock:
        q = q.with_for_update()
    return (await db.execute(q)).scalar_one_or_none()


async def mark_paid(db: AsyncSession, payment: Payment, *, gateway_data: dict | None = None, actor: User | None = None,
                    note: str | None = None, provider_label: str | None = None) -> Payment:
    """Idempotent: safe to call from verify, webhook and admin confirm."""
    if payment.status == PaymentStatus.PAID:
        return payment
    payment.status = PaymentStatus.PAID
    payment.paid_at = datetime.now(timezone.utc)
    if gateway_data:
        payment.gateway_payload = gateway_data
        payment.channel = gateway_data.get("channel") or payment.channel
        payment.gateway_response = gateway_data.get("gateway_response") or "Successful"
    else:
        payment.gateway_response = provider_label or "Manually confirmed"
    if actor:
        payment.confirmed_by_id = actor.id
    if note:
        payment.admin_note = note
    order_number = None
    if payment.order_id:
        order = await order_service.get_order(db, payment.order_id)
        order_number = order.number
        await db.flush()
        paid = await paid_total(db, order.id)
        if paid >= Decimal(order.total) - Decimal("0.01"):
            order.payment_status = PaymentStatus.PAID
            order.paid_at = payment.paid_at
            if order.status == OrderStatus.PENDING:
                await order_service.set_status(db, order, OrderStatus.CONFIRMED, note="Payment received", actor=actor, notify=False)
        else:
            order.payment_status = PaymentStatus.PENDING
            order_service.add_history(order, "partial_payment", f"Part payment of ₦{payment.amount:,.2f} received", actor.id if actor else None)
    await db.flush()
    await send_email(db, payment.email, "Payment received — thank you", "payment_receipt.html", payment=payment, order_number=order_number, order_id=payment.order_id)
    await notify_admin(db, f"Payment received ₦{payment.amount:,.0f}", f"Ref {payment.reference} {('for order ' + order_number) if order_number else '(direct)'} from {payment.email}")
    return payment


async def mark_failed(db: AsyncSession, payment: Payment, reason: str | None = None) -> None:
    if payment.status in (PaymentStatus.PAID, PaymentStatus.REFUNDED):
        return
    payment.status = PaymentStatus.FAILED
    payment.gateway_response = reason or payment.gateway_response
    if payment.order_id:
        order = await order_service.get_order(db, payment.order_id)
        if order.payment_status == PaymentStatus.PENDING and await paid_total(db, order.id) == 0:
            order.payment_status = PaymentStatus.UNPAID


async def verify_reference(db: AsyncSession, reference: str, *, actor: User | None = None) -> Payment:
    """Verify with Paystack (source of truth) and settle the payment."""
    payment = await get_by_reference(db, reference, lock=True)
    if not payment:
        raise NotFound("Payment not found.")
    if payment.status == PaymentStatus.PAID:
        return payment
    if paystack_service.is_mock_mode():
        # dev-only simulated gateway; the callback adds mock=1 and the client calls /payments/verify
        return await mark_paid(db, payment, gateway_data={"channel": "mock", "gateway_response": "Mock payment (dev)"}, actor=actor)
    data = await paystack_service.verify(reference)
    return await _settle_from_gateway(db, payment, data, actor)


async def _settle_from_gateway(db: AsyncSession, payment: Payment, data: dict, actor: User | None = None) -> Payment:
    status = data.get("status")
    if status == "success":
        if int(data.get("amount", 0)) != paystack_service.to_kobo(payment.amount) or data.get("currency", "NGN") != payment.currency:
            payment.gateway_response = "Amount mismatch — flagged for review"
            payment.gateway_payload = data
            log.error("amount mismatch for %s: %s vs %s", payment.reference, data.get("amount"), payment.amount)
            raise PaymentError("Payment amount mismatch. Our team has been notified.", code="amount_mismatch")
        return await mark_paid(db, payment, gateway_data=data, actor=actor)
    if status in ("failed", "abandoned", "reversed"):
        await mark_failed(db, payment, data.get("gateway_response") or status)
    else:
        payment.gateway_response = data.get("gateway_response") or status
    return payment


async def handle_webhook(db: AsyncSession, event: dict) -> None:
    name, data = event.get("event"), event.get("data") or {}
    ref = data.get("reference")
    if not ref:
        return
    payment = await get_by_reference(db, ref, lock=True)
    if not payment:
        log.warning("webhook for unknown reference %s", ref)
        return
    if name == "charge.success":
        await _settle_from_gateway(db, payment, data)
    elif name in ("charge.failed",):
        await mark_failed(db, payment, data.get("gateway_response"))
    elif name in ("refund.processed",) and payment.status == PaymentStatus.PAID:
        payment.status = PaymentStatus.REFUNDED
        if payment.order_id:
            order = await order_service.get_order(db, payment.order_id)
            order.payment_status = PaymentStatus.REFUNDED


async def admin_confirm(db: AsyncSession, payment: Payment, actor: User, *, note: str | None = None, manual: bool = False) -> Payment:
    """Admin 'try to confirm': re-verify with the gateway; if unresolved and manual=True accept bank-transfer style confirmation."""
    if payment.status == PaymentStatus.PAID:
        return payment
    if payment.provider == PaymentProvider.PAYSTACK and not manual:
        return await verify_reference(db, payment.reference, actor=actor)
    return await mark_paid(db, payment, actor=actor, note=note, provider_label="Manually confirmed by admin")


async def record_manual_payment(db: AsyncSession, order: Order, amount: Decimal, actor: User, note: str | None, channel: str) -> Payment:
    p = Payment(reference=new_reference("SRM"), purpose=PaymentPurpose.ORDER, provider=PaymentProvider.MANUAL, status=PaymentStatus.PENDING,
                order_id=order.id, user_id=order.user_id, email=order.customer_email, payer_name=order.customer_name, phone=order.customer_phone,
                amount=amount, description=f"Manual payment for {order.number}", channel=channel)
    db.add(p)
    await db.flush()
    return await mark_paid(db, p, actor=actor, note=note, provider_label=f"Recorded by {actor.full_name}")
