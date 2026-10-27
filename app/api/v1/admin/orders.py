import uuid
from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import and_, or_, select

from app.api.deps import DB, CurrentUser, require_permissions
from app.core.exceptions import AppError
from app.enums import AssignmentStatus, OrderChannel, OrderStatus, PaymentMethod, PaymentStatus, Permission as P
from app.models import Order, ShippingRate, Store, User
from app.schemas.common import Message, Page
from app.schemas.order import (AdminOrderCreate, AdminOrderOut, CheckoutResponse, OrderOut, OrderStatusUpdate, OrderUpdate, ShippingRateIn,
                               ShippingRateOut, StoreAssign)
from app.schemas.payment import ManualPaymentCreate, PaymentOut
from app.schemas.store import SuggestStoreOut, StorePublic
from app.services import checkout_service, order_service, payment_service, store_service
from app.services.crud import CRUDService
from app.utils.pagination import PageParams, page_of, paginate

router = APIRouter(prefix="/admin", tags=["admin:orders"])
view = Depends(require_permissions(P.ORDERS_VIEW, P.ORDERS_MANAGE, any_of=True))
manage = Depends(require_permissions(P.ORDERS_MANAGE))


@router.get("/orders", response_model=Page[AdminOrderOut], dependencies=[view])
async def list_orders(db: DB, params: PageParams = Depends(), q: str | None = None, status: OrderStatus | None = None,
                      payment_status: PaymentStatus | None = None, channel: OrderChannel | None = None, state: str | None = None,
                      store_id: uuid.UUID | None = None, wholesale: bool | None = None, needs_store_approval: bool | None = None,
                      date_from: datetime | None = None, date_to: datetime | None = None):
    stmt = select(Order)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(or_(Order.number.ilike(like), Order.customer_name.ilike(like), Order.customer_email.ilike(like), Order.customer_phone.ilike(like)))
    for col, val in ((Order.status, status), (Order.payment_status, payment_status), (Order.channel, channel), (Order.assigned_store_id, store_id),
                     (Order.is_wholesale, wholesale)):
        if val is not None:
            stmt = stmt.where(col == val)
    if state:
        stmt = stmt.where(Order.delivery_state.ilike(state))
    if needs_store_approval:
        stmt = stmt.where(Order.assignment_status == AssignmentStatus.SUGGESTED)
    if date_from:
        stmt = stmt.where(Order.created_at >= date_from)
    if date_to:
        stmt = stmt.where(Order.created_at <= date_to)
    rows, total, pages = await paginate(db, stmt.order_by(Order.created_at.desc()), params, unique=True)
    return page_of(rows, total, pages, params)


@router.post("/orders", response_model=CheckoutResponse, status_code=201, dependencies=[manage])
async def create_order(data: AdminOrderCreate, db: DB, actor: CurrentUser):
    """Create an order on behalf of a customer (phone / WhatsApp / email / walk-in)."""
    customer = await db.get(User, data.user_id) if data.user_id else None
    channel = data.channel if data.channel != OrderChannel.WEB else OrderChannel.ADMIN
    order = await order_service.create_order(db, data, customer, actor=actor, channel=channel, delivery_fee_override=data.delivery_fee_override)
    payment = None
    if data.mark_paid:
        payment = await payment_service.record_manual_payment(db, order, order.total, actor, "Marked paid at order creation", data.payment_method.value)
    elif data.payment_method == PaymentMethod.PAYSTACK:
        payment = await payment_service.init_for_order(db, order)
    await order_service.notify_order_created(db, order)
    await db.refresh(order)
    step = "confirmation" if data.mark_paid else ("pay_online" if data.payment_method == PaymentMethod.PAYSTACK else data.payment_method.value)
    return CheckoutResponse(order=OrderOut.model_validate(order), authorization_url=None if data.mark_paid else (payment.authorization_url if payment else None),
                            payment_reference=payment.reference if payment else None, next_step=step)


@router.get("/orders/{order_id}", response_model=AdminOrderOut, dependencies=[view])
async def get_order(order_id: uuid.UUID, db: DB):
    return await order_service.get_order(db, order_id)


@router.patch("/orders/{order_id}", response_model=AdminOrderOut, dependencies=[manage])
async def update_order(order_id: uuid.UUID, data: OrderUpdate, db: DB):
    o = await order_service.get_order(db, order_id)
    patch = data.model_dump(exclude_unset=True)
    if "delivery_fee" in patch and patch["delivery_fee"] is not None:
        o.total = o.total - o.delivery_fee + patch["delivery_fee"]
    for k, v in patch.items():
        setattr(o, k, v)
    return o


@router.post("/orders/{order_id}/status", response_model=AdminOrderOut, dependencies=[manage])
async def update_status(order_id: uuid.UUID, data: OrderStatusUpdate, db: DB, actor: CurrentUser):
    o = await order_service.get_order(db, order_id)
    await order_service.set_status(db, o, data.status, note=data.note, actor=actor, notify=data.notify_customer, is_public=data.is_public)
    await db.refresh(o)
    return o


@router.post("/orders/{order_id}/assign-store", response_model=AdminOrderOut, dependencies=[Depends(require_permissions(P.ORDERS_MANAGE, P.STORES_MANAGE, any_of=True))])
async def assign_store(order_id: uuid.UUID, data: StoreAssign, db: DB, actor: CurrentUser):
    o = await order_service.get_order(db, order_id)
    return await order_service.assign_store(db, o, data.store_id, actor)


@router.post("/orders/{order_id}/suggest-store", response_model=SuggestStoreOut, dependencies=[manage])
async def suggest_store(order_id: uuid.UUID, db: DB):
    """Run the system matcher (state / coordinates). The suggestion needs admin approval before it assigns."""
    o = await order_service.get_order(db, order_id)
    found = await store_service.nearest_store(db, state=o.delivery_state, lat=o.shipping_address.get("latitude"), lng=o.shipping_address.get("longitude"), public_only=False)
    if not found:
        return SuggestStoreOut(store=None, reason="No approved store covers this location.")
    store, dist = found[0]
    o.suggested_store_id, o.assignment_status = store.id, AssignmentStatus.SUGGESTED
    out = StorePublic.model_validate(store)
    out.distance_km = round(dist, 1) if dist is not None else None
    return SuggestStoreOut(store=out, reason="Awaiting admin approval")


@router.post("/orders/{order_id}/approve-store", response_model=AdminOrderOut, dependencies=[manage])
async def approve_store(order_id: uuid.UUID, db: DB, actor: CurrentUser):
    o = await order_service.get_order(db, order_id)
    if not o.suggested_store_id:
        raise AppError("There is no suggested store to approve.", code="no_suggestion")
    return await order_service.assign_store(db, o, o.suggested_store_id, actor, approve_suggestion=True)


@router.post("/orders/{order_id}/reject-store", response_model=AdminOrderOut, dependencies=[manage])
async def reject_store(order_id: uuid.UUID, db: DB, actor: CurrentUser):
    return await order_service.reject_suggestion(db, await order_service.get_order(db, order_id), actor)


@router.post("/orders/{order_id}/payments", response_model=PaymentOut, status_code=201, dependencies=[Depends(require_permissions(P.PAYMENTS_CONFIRM))])
async def record_payment(order_id: uuid.UUID, data: ManualPaymentCreate, db: DB, actor: CurrentUser):
    o = await order_service.get_order(db, order_id)
    return await payment_service.record_manual_payment(db, o, data.amount, actor, data.note, data.channel)


# ---- shipping rates ----
rates = CRUDService(ShippingRate, "Shipping rate")


@router.get("/shipping-rates", response_model=list[ShippingRateOut], dependencies=[view])
async def list_rates(db: DB):
    return await rates.all(db, ShippingRate.state)


@router.post("/shipping-rates", response_model=ShippingRateOut, status_code=201, dependencies=[manage])
async def create_rate(data: ShippingRateIn, db: DB):
    return await rates.create(db, data)


@router.patch("/shipping-rates/{rid}", response_model=ShippingRateOut, dependencies=[manage])
async def update_rate(rid: uuid.UUID, data: ShippingRateIn, db: DB):
    return await rates.update(db, await rates.get(db, rid), data)


@router.delete("/shipping-rates/{rid}", response_model=Message, dependencies=[manage])
async def delete_rate(rid: uuid.UUID, db: DB):
    await rates.delete(db, await rates.get(db, rid))
    return Message(detail="Shipping rate deleted")
