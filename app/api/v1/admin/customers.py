import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import func, or_, select

from app.api.deps import DB, require_permissions
from app.core.exceptions import NotFound
from app.enums import OrderStatus, Permission as P, UserType
from app.models import Order, Store, User
from app.schemas.common import Page
from app.schemas.order import OrderOut
from app.schemas.store import SuggestStoreOut, StorePublic
from app.schemas.user import AddressOut, AdminUserUpdate, CustomerListItem
from app.services import store_service
from app.utils.pagination import PageParams, page_of, paginate

router = APIRouter(prefix="/admin/customers", tags=["admin:customers"])
view = Depends(require_permissions(P.CUSTOMERS_VIEW))
manage = Depends(require_permissions(P.CUSTOMERS_MANAGE))


@router.get("", response_model=Page[CustomerListItem], dependencies=[view])
async def list_customers(db: DB, params: PageParams = Depends(), q: str | None = None, store_id: uuid.UUID | None = None):
    stmt = select(User).where(User.user_type == UserType.CUSTOMER)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(or_(User.email.ilike(like), User.first_name.ilike(like), User.last_name.ilike(like), User.phone.ilike(like)))
    if store_id:
        stmt = stmt.where(User.linked_store_id == store_id)
    rows, total, pages = await paginate(db, stmt.order_by(User.created_at.desc()), params, unique=True)
    stats = {}
    if rows:
        agg = (await db.execute(select(Order.user_id, func.count(), func.coalesce(func.sum(Order.total), 0))
                                .where(Order.user_id.in_([r.id for r in rows]), Order.status != OrderStatus.CANCELLED).group_by(Order.user_id))).all()
        stats = {uid: (c, float(t)) for uid, c, t in agg}
    items = []
    for r in rows:
        item = CustomerListItem.model_validate(r)
        item.order_count, item.total_spent = stats.get(r.id, (0, 0))
        item.notes = r.notes
        items.append(item)
    return page_of(items, total, pages, params)


@router.get("/{user_id}", dependencies=[view])
async def customer_detail(user_id: uuid.UUID, db: DB):
    u = await db.get(User, user_id)
    if not u:
        raise NotFound("Customer not found.")
    orders = (await db.execute(select(Order).where(Order.user_id == u.id).order_by(Order.created_at.desc()))).unique().scalars().all()
    return {
        "customer": CustomerListItem.model_validate(u).model_copy(update={"notes": u.notes}),
        "addresses": [AddressOut.model_validate(a) for a in u.addresses],
        "orders": [OrderOut.model_validate(o) for o in orders],
        "linked_store": StorePublic.model_validate(await db.get(Store, u.linked_store_id)) if u.linked_store_id else None,
    }


@router.patch("/{user_id}", dependencies=[manage])
async def update_customer(user_id: uuid.UUID, data: AdminUserUpdate, db: DB):
    u = await db.get(User, user_id)
    if not u:
        raise NotFound("Customer not found.")
    for k in ("first_name", "last_name", "phone", "is_active", "linked_store_id", "notes"):
        if k in data.model_fields_set:
            setattr(u, k, getattr(data, k))
    return CustomerListItem.model_validate(u)


@router.post("/{user_id}/suggest-store", response_model=SuggestStoreOut, dependencies=[view])
async def suggest_for_customer(user_id: uuid.UUID, db: DB):
    """System proposes the closest store from the customer's default address; admin then links it with PATCH linked_store_id."""
    u = await db.get(User, user_id)
    if not u:
        raise NotFound("Customer not found.")
    addr = next((a for a in u.addresses if a.is_default), u.addresses[0] if u.addresses else None)
    if not addr:
        return SuggestStoreOut(store=None, reason="Customer has no saved address.")
    found = await store_service.nearest_store(db, state=addr.state, lat=addr.latitude, lng=addr.longitude, public_only=False)
    if not found:
        return SuggestStoreOut(store=None, reason="No approved store covers this location.")
    s, d = found[0]
    out = StorePublic.model_validate(s)
    out.distance_km = round(d, 1) if d is not None else None
    return SuggestStoreOut(store=out, reason="Closest approved store (requires your approval to link)")
