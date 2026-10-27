import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select

from app.api.deps import DB, CurrentUser, require_permissions
from app.core.exceptions import Forbidden, NotFound
from app.enums import OrderStatus, Permission as P
from app.models import Order, Store
from app.schemas.order import AdminOrderOut, OrderStatusUpdate
from app.schemas.store import StoreOut
from app.services import order_service

router = APIRouter(prefix="/partner", tags=["partner"], dependencies=[Depends(require_permissions(P.PARTNER_PORTAL))])
ALLOWED_PARTNER = {OrderStatus.PROCESSING, OrderStatus.DISPATCHED, OrderStatus.DELIVERED}


async def _my_store(db, user) -> Store:
    s = (await db.execute(select(Store).where(Store.owner_user_id == user.id))).scalars().first()
    if not s:
        raise NotFound("No store is linked to your account yet.")
    return s


@router.get("/store", response_model=StoreOut)
async def store(db: DB, user: CurrentUser):
    return await _my_store(db, user)


@router.get("/orders", response_model=list[AdminOrderOut])
async def orders(db: DB, user: CurrentUser):
    s = await _my_store(db, user)
    return (await db.execute(select(Order).where(Order.assigned_store_id == s.id).order_by(Order.created_at.desc()))).unique().scalars().all()


@router.post("/orders/{order_id}/status", response_model=AdminOrderOut)
async def update_status(order_id: uuid.UUID, data: OrderStatusUpdate, db: DB, user: CurrentUser):
    s = await _my_store(db, user)
    o = await order_service.get_order(db, order_id)
    if o.assigned_store_id != s.id:
        raise Forbidden("This order is not assigned to your store.")
    if data.status not in ALLOWED_PARTNER:
        raise Forbidden("You can only mark orders as processing, dispatched or delivered.")
    await order_service.set_status(db, o, data.status, note=data.note, actor=user, notify=data.notify_customer)
    return o
