import secrets
import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import AppError, Forbidden, NotFound
from app.enums import (AssignmentStatus, OrderChannel, OrderStatus, PaymentMethod, PaymentStatus, StoreStatus)
from app.models import Address, Order, OrderItem, OrderStatusHistory, ProductVariant, Promotion, Store, User
from app.schemas.order import CheckoutRequest
from app.services import store_service
from app.services.email_service import notify_admin, send_email
from app.services.pricing_service import PricingResult, price_cart
from app.services.settings_service import get_setting
from app.utils.text import normalize_email, normalize_phone

STATUS_LABELS = {
    OrderStatus.PENDING: "Order placed",
    OrderStatus.CONFIRMED: "Order confirmed",
    OrderStatus.PROCESSING: "We're preparing your order",
    OrderStatus.DISPATCHED: "Your order is on its way",
    OrderStatus.DELIVERED: "Delivered",
    OrderStatus.COMPLETED: "Completed",
    OrderStatus.CANCELLED: "Order cancelled",
    OrderStatus.REFUNDED: "Order refunded",
}


def new_order_number() -> str:
    return f"SR-{datetime.now(timezone.utc):%y%m%d}-{secrets.randbelow(90000) + 10000}"


async def unique_order_number(db: AsyncSession) -> str:
    for _ in range(10):
        n = new_order_number()
        if not (await db.execute(select(Order.id).where(Order.number == n))).first():
            return n
    return f"SR-{uuid.uuid4().hex[:10].upper()}"


def add_history(order: Order, status: str, note: str | None = None, actor_id: uuid.UUID | None = None, is_public: bool = True) -> None:
    order.history.append(OrderStatusHistory(order_id=order.id, status=status, note=note, actor_id=actor_id, is_public=is_public))


async def get_order(db: AsyncSession, order_id: uuid.UUID) -> Order:
    order = (await db.execute(select(Order).where(Order.id == order_id))).unique().scalar_one_or_none()
    if not order:
        raise NotFound("Order not found.")
    return order


async def get_order_by_number(db: AsyncSession, number: str) -> Order | None:
    return (await db.execute(select(Order).where(Order.number == number.strip().upper()))).unique().scalar_one_or_none()


async def resolve_user_by_email(db: AsyncSession, email: str) -> User | None:
    return (await db.execute(select(User).where(User.email == normalize_email(email)))).scalar_one_or_none()


async def _resolve_address(db: AsyncSession, data: CheckoutRequest, user: User | None) -> tuple[dict, Address | None]:
    if data.address_id:
        if not user:
            raise Forbidden("Sign in to use a saved address.")
        addr = (await db.execute(select(Address).where(Address.id == data.address_id, Address.user_id == user.id))).scalar_one_or_none()
        if not addr:
            raise NotFound("Saved address not found.")
        return _snapshot(addr), addr
    if not data.address:
        raise AppError("A delivery address is required.", code="address_required")
    a = data.address
    snap = a.model_dump(exclude={"is_default"})
    snap["phone"] = normalize_phone(a.phone)
    saved = None
    if user and data.save_address:
        if a.is_default:
            for other in (await db.execute(select(Address).where(Address.user_id == user.id))).scalars():
                other.is_default = False
        saved = Address(user_id=user.id, **{**a.model_dump(), "phone": snap["phone"]})
        db.add(saved)
        await db.flush()
    return snap, saved


def _snapshot(a: Address) -> dict:
    return {k: getattr(a, k) for k in ("label", "recipient_name", "phone", "line1", "line2", "city", "state", "lga", "country", "latitude", "longitude")}


async def create_order(db: AsyncSession, data: CheckoutRequest, user: User | None, *, priced: PricingResult | None = None,
                       actor: User | None = None, channel: OrderChannel | None = None, delivery_fee_override: Decimal | None = None) -> Order:
    # contact
    name = data.name or (user.full_name if user else None)
    email = data.email or (user.email if user else None)
    phone = normalize_phone(data.phone or (user.phone if user else None))
    if not (name and email and phone):
        raise AppError("Name, email and phone are required.", code="contact_required")
    email = normalize_email(email)
    linked_user = user or await resolve_user_by_email(db, email)

    snap, addr = await _resolve_address(db, data, user)
    state = snap.get("state")
    pricing = priced or await price_cart(db, data.items, state=state, coupon_code=data.coupon_code, strict_coupon=bool(data.coupon_code), enforce_stock=True)
    commerce = pricing.commerce
    fee = delivery_fee_override if delivery_fee_override is not None else pricing.delivery_fee
    total = pricing.subtotal - pricing.coupon_discount + fee

    if data.payment_method == PaymentMethod.PAYSTACK and pricing.is_wholesale and not commerce.get("allow_online_wholesale", True):
        raise AppError("Wholesale orders are completed through WhatsApp or bank transfer.", code="wholesale_offline_only")

    order = Order(
        number=await unique_order_number(db), user_id=linked_user.id if linked_user else None,
        customer_name=name, customer_email=email, customer_phone=phone, shipping_address=snap, address_id=addr.id if addr else None,
        delivery_state=state, status=OrderStatus.PENDING, payment_status=PaymentStatus.UNPAID, payment_method=data.payment_method,
        channel=channel or data.channel, is_wholesale=pricing.is_wholesale, total_packs=pricing.total_packs,
        subtotal=pricing.subtotal, discount_total=pricing.coupon_discount, delivery_fee=fee, total=total,
        coupon_code=pricing.coupon.code if pricing.coupon else None, promotion_id=pricing.coupon.id if pricing.coupon else None,
        notes=data.notes, history=[],
    )
    for l in pricing.lines:
        order.items.append(OrderItem(
            product_id=l.variant.product_id, variant_id=l.variant.id, product_name=l.variant.product.name, variant_label=l.variant.label,
            sku=l.variant.sku, image_url=l.variant.image_url or ((l.variant.product.images or [None])[0]), unit_price=l.unit,
            quantity=l.quantity, pack_equivalent=l.variant.pack_equivalent, line_total=l.total,
        ))
        if l.variant.track_stock:
            l.variant.stock -= l.quantity
    if pricing.coupon:
        pricing.coupon.used_count += 1
    db.add(order)
    await db.flush()
    add_history(order, OrderStatus.PENDING.value, "Order placed", actor.id if actor else None)

    # store / dealer fulfilment
    if data.preferred_store_id:
        store = (await db.execute(select(Store).where(Store.id == data.preferred_store_id, Store.status == StoreStatus.APPROVED))).scalar_one_or_none()
        if store:
            order.suggested_store_id = store.id
            order.assignment_status = AssignmentStatus.SUGGESTED
    elif data.request_store_match or commerce.get("auto_suggest_store"):
        found = await store_service.nearest_store(db, state=state, lat=snap.get("latitude"), lng=snap.get("longitude"), public_only=False)
        if found:
            order.suggested_store_id = found[0][0].id
            order.assignment_status = AssignmentStatus.SUGGESTED
    await db.flush()
    await db.refresh(order)
    return order


async def restore_stock(db: AsyncSession, order: Order) -> None:
    for item in order.items:
        if item.variant_id:
            v = await db.get(ProductVariant, item.variant_id)
            if v and v.track_stock:
                v.stock += item.quantity


async def set_status(db: AsyncSession, order: Order, status: OrderStatus, *, note: str | None = None, actor: User | None = None,
                     notify: bool = True, is_public: bool = True) -> Order:
    if order.status == status:
        return order
    if order.status in (OrderStatus.CANCELLED, OrderStatus.REFUNDED) and status not in (OrderStatus.PENDING,):
        raise AppError("A cancelled or refunded order cannot be moved forward.", code="invalid_transition")
    if status == OrderStatus.CANCELLED:
        if order.status in (OrderStatus.DISPATCHED, OrderStatus.DELIVERED, OrderStatus.COMPLETED):
            raise AppError("Dispatched orders cannot be cancelled.", code="invalid_transition")
        await restore_stock(db, order)
    order.status = status
    if status == OrderStatus.REFUNDED:
        order.payment_status = PaymentStatus.REFUNDED
    add_history(order, status.value, note or STATUS_LABELS.get(status), actor.id if actor else None, is_public)
    await db.flush()
    if notify:
        await send_email(db, order.customer_email, f"Order {order.number}: {STATUS_LABELS.get(status, status.value)}", "order_status.html",
                         order=order, note=note, order_id=order.id)
    return order


async def notify_order_created(db: AsyncSession, order: Order) -> None:
    bank = None
    if order.payment_method == PaymentMethod.BANK_TRANSFER:
        from app.services import provider_service
        row = await provider_service.get_row(db, "bank_transfer")
        if row and row.is_enabled and (row.extra or {}).get("account_number"):  # structured details saved by the admin
            e = row.extra
            bank = f"{e.get('bank_name', '')} · {e.get('account_name', '')} · {e.get('account_number', '')}" + (f" ({e['instructions']})" if e.get("instructions") else "")
        else:
            bank = (await get_setting(db, "commerce")).get("bank_details")
    await send_email(db, order.customer_email, f"We received your order {order.number}", "order_confirmation.html",
                     order=order, bank_details=bank, order_id=order.id)
    await notify_admin(db, f"New order {order.number} — ₦{order.total:,.0f}",
                       f"{order.customer_name} ({order.customer_email}, {order.customer_phone}) placed {order.number}\n"
                       f"Packs: {order.total_packs} | Channel: {order.channel.value} | Method: {order.payment_method.value}\nState: {order.delivery_state}")


async def assign_store(db: AsyncSession, order: Order, store_id: uuid.UUID | None, actor: User | None, approve_suggestion: bool = False) -> Order:
    if store_id is None:
        order.assigned_store_id = None
        order.assignment_status = AssignmentStatus.NONE
        add_history(order, "store_unassigned", "Store assignment removed", actor.id if actor else None, is_public=False)
    else:
        store = await db.get(Store, store_id)
        if not store or store.status != StoreStatus.APPROVED:
            raise AppError("Store must exist and be approved.", code="invalid_store")
        order.assigned_store_id = store.id
        order.assignment_status = AssignmentStatus.ASSIGNED
        order.suggested_store_id = store.id if approve_suggestion else order.suggested_store_id
        add_history(order, "store_assigned", f"Assigned to {store.name} ({store.state})", actor.id if actor else None)
    await db.flush()
    await db.refresh(order)
    return order


async def reject_suggestion(db: AsyncSession, order: Order, actor: User | None) -> Order:
    order.assignment_status = AssignmentStatus.REJECTED
    add_history(order, "store_suggestion_rejected", "Store suggestion rejected", actor.id if actor else None, is_public=False)
    await db.flush()
    return order


def public_history(order: Order):
    return [h for h in order.history if h.is_public]
