import uuid
from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends
from sqlalchemy import func, or_, select

from app.api.deps import DB, CurrentUser, require_permissions
from app.core.exceptions import NotFound
from app.enums import PaymentProvider, PaymentPurpose, PaymentStatus, Permission as P
from app.models import Order, Payment
from app.schemas.common import Page
from app.schemas.payment import ManualConfirm, PaymentOut
from app.services import payment_service
from app.utils.pagination import PageParams, page_of, paginate

router = APIRouter(prefix="/admin/payments", tags=["admin:payments"])
view = Depends(require_permissions(P.PAYMENTS_VIEW))
confirm = Depends(require_permissions(P.PAYMENTS_CONFIRM))


async def _out(db, p: Payment) -> PaymentOut:
    o = PaymentOut.model_validate(p)
    if p.order_id:
        o.order_number = (await db.execute(select(Order.number).where(Order.id == p.order_id))).scalar_one_or_none()
    return o


@router.get("", response_model=Page[PaymentOut], dependencies=[view])
async def list_payments(db: DB, params: PageParams = Depends(), q: str | None = None, status: PaymentStatus | None = None,
                        purpose: PaymentPurpose | None = None, provider: PaymentProvider | None = None,
                        date_from: datetime | None = None, date_to: datetime | None = None):
    stmt = select(Payment)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(or_(Payment.reference.ilike(like), Payment.email.ilike(like), Payment.payer_name.ilike(like)))
    for col, val in ((Payment.status, status), (Payment.purpose, purpose), (Payment.provider, provider)):
        if val is not None:
            stmt = stmt.where(col == val)
    if date_from:
        stmt = stmt.where(Payment.created_at >= date_from)
    if date_to:
        stmt = stmt.where(Payment.created_at <= date_to)
    rows, total, pages = await paginate(db, stmt.order_by(Payment.created_at.desc()), params)
    numbers = dict((await db.execute(select(Order.id, Order.number).where(Order.id.in_([r.order_id for r in rows if r.order_id])))).all()) if rows else {}
    items = []
    for r in rows:
        o = PaymentOut.model_validate(r)
        o.order_number = numbers.get(r.order_id)
        items.append(o)
    return page_of(items, total, pages, params)


@router.get("/stats", dependencies=[view])
async def stats(db: DB):
    rows = (await db.execute(select(Payment.status, func.count(), func.coalesce(func.sum(Payment.amount), 0)).group_by(Payment.status))).all()
    return {(s.value if hasattr(s, "value") else s): {"count": c, "amount": float(a)} for s, c, a in rows}


@router.get("/{payment_id}", response_model=PaymentOut, dependencies=[view])
async def get_payment(payment_id: uuid.UUID, db: DB):
    p = await db.get(Payment, payment_id)
    if not p:
        raise NotFound("Payment not found.")
    return await _out(db, p)


@router.post("/{payment_id}/verify", response_model=PaymentOut, dependencies=[confirm])
async def verify_payment(payment_id: uuid.UUID, db: DB, actor: CurrentUser):
    """Admin 'try to confirm': re-checks the transaction with Paystack and settles the order if successful."""
    p = await db.get(Payment, payment_id)
    if not p:
        raise NotFound("Payment not found.")
    p = await payment_service.admin_confirm(db, p, actor)
    return await _out(db, p)


@router.post("/{payment_id}/confirm-manually", response_model=PaymentOut, dependencies=[confirm])
async def confirm_manually(payment_id: uuid.UUID, data: ManualConfirm, db: DB, actor: CurrentUser):
    """Force-confirm (e.g. bank transfer seen in the bank app). Always leaves an audit note."""
    p = await db.get(Payment, payment_id)
    if not p:
        raise NotFound("Payment not found.")
    p = await payment_service.admin_confirm(db, p, actor, note=data.note or "Confirmed manually", manual=True)
    return await _out(db, p)
