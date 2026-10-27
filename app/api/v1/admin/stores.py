import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import or_, select

from app.api.deps import DB, CurrentUser, require_permissions
from app.core.exceptions import AppError, NotFound
from app.core.security import hash_password
from app.enums import ApplicationStatus, Permission as P, StoreStatus, UserType
from app.models import DistributorApplication, Role, Store, User
from app.schemas.common import Message, Page
from app.schemas.store import ApplicationOut, ApplicationUpdate, ApproveApplication, StoreIn, StoreOut, StoreUpdate
from app.core.security import generate_numeric_code
from app.services import store_service
from app.services.email_service import send_email
from app.utils.pagination import PageParams, page_of, paginate
from app.utils.text import normalize_phone

router = APIRouter(prefix="/admin", tags=["admin:stores"])
view = Depends(require_permissions(P.STORES_VIEW, P.STORES_MANAGE, any_of=True))
manage = Depends(require_permissions(P.STORES_MANAGE))


@router.get("/stores", response_model=Page[StoreOut], dependencies=[view])
async def list_stores(db: DB, params: PageParams = Depends(), q: str | None = None, state: str | None = None, status: StoreStatus | None = None,
                      is_public: bool | None = None):
    stmt = select(Store)
    if q:
        stmt = stmt.where(or_(Store.name.ilike(f"%{q}%"), Store.city.ilike(f"%{q}%"), Store.address.ilike(f"%{q}%")))
    if state:
        stmt = stmt.where(Store.state.ilike(state))
    if status:
        stmt = stmt.where(Store.status == status)
    if is_public is not None:
        stmt = stmt.where(Store.is_public.is_(is_public))
    rows, total, pages = await paginate(db, stmt.order_by(Store.state, Store.name), params)
    return page_of(rows, total, pages, params)


@router.post("/stores", response_model=StoreOut, status_code=201, dependencies=[manage])
async def create_store(data: StoreIn, db: DB):
    s = Store(**data.model_dump(), slug=await store_service.unique_store_slug(db, data.name))
    db.add(s)
    await db.flush()
    return s


@router.get("/stores/{store_id}", response_model=StoreOut, dependencies=[view])
async def get_store(store_id: uuid.UUID, db: DB):
    s = await db.get(Store, store_id)
    if not s:
        raise NotFound("Store not found.")
    return s


@router.patch("/stores/{store_id}", response_model=StoreOut, dependencies=[manage])
async def update_store(store_id: uuid.UUID, data: StoreUpdate, db: DB):
    s = await db.get(Store, store_id)
    if not s:
        raise NotFound("Store not found.")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(s, k, v)
    if "name" in data.model_fields_set and data.name:
        s.slug = await store_service.unique_store_slug(db, data.name, exclude=s.id)
    return s


@router.delete("/stores/{store_id}", response_model=Message, dependencies=[manage])
async def delete_store(store_id: uuid.UUID, db: DB):
    s = await db.get(Store, store_id)
    if not s:
        raise NotFound("Store not found.")
    await db.delete(s)
    return Message(detail="Store deleted")


# ---- distributor / store signups ----
@router.get("/applications", response_model=Page[ApplicationOut], dependencies=[view])
async def list_applications(db: DB, params: PageParams = Depends(), status: ApplicationStatus | None = None, q: str | None = None):
    stmt = select(DistributorApplication)
    if status:
        stmt = stmt.where(DistributorApplication.status == status)
    if q:
        stmt = stmt.where(or_(DistributorApplication.business_name.ilike(f"%{q}%"), DistributorApplication.email.ilike(f"%{q}%")))
    rows, total, pages = await paginate(db, stmt.order_by(DistributorApplication.created_at.desc()), params)
    return page_of(rows, total, pages, params)


@router.patch("/applications/{app_id}", response_model=ApplicationOut, dependencies=[manage])
async def update_application(app_id: uuid.UUID, data: ApplicationUpdate, db: DB):
    a = await db.get(DistributorApplication, app_id)
    if not a:
        raise NotFound("Application not found.")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(a, k, v)
    a.reviewed_at = datetime.now(timezone.utc)
    return a


@router.post("/applications/{app_id}/approve", response_model=StoreOut, dependencies=[manage])
async def approve_application(app_id: uuid.UUID, data: ApproveApplication, db: DB, actor: CurrentUser):
    """Approve → creates the Store (public only if admin chooses) and optionally a partner portal account."""
    a = await db.get(DistributorApplication, app_id)
    if not a:
        raise NotFound("Application not found.")
    if a.store_id:
        raise AppError("Application already approved.", code="already_approved")
    state = data.state or a.state
    address = data.address or a.location
    if not state:
        raise AppError("State is required to create the store.", code="state_required")
    store = Store(name=a.business_name, slug=await store_service.unique_store_slug(db, a.business_name), store_type=data.store_type,
                  status=StoreStatus.APPROVED, is_public=data.is_public, contact_person=a.contact_person, phone=a.phone, whatsapp=a.phone,
                  email=a.email, address=address, city=data.city, state=state)
    db.add(store)
    await db.flush()
    temp_pw = None
    if data.create_partner_account:
        existing = (await db.execute(select(User).where(User.email == a.email))).scalar_one_or_none()
        role = (await db.execute(select(Role).where(Role.key == "store_partner"))).scalar_one_or_none()
        if existing is None:
            temp_pw = generate_numeric_code(4) + "Sr" + generate_numeric_code(4)
            first, _, last = a.contact_person.partition(" ")
            user = User(email=a.email, password_hash=hash_password(temp_pw), first_name=first, last_name=last, phone=normalize_phone(a.phone),
                        user_type=UserType.PARTNER, role_id=role.id if role else None, email_verified_at=datetime.now(timezone.utc))
            db.add(user)
            await db.flush()
            store.owner_user_id = user.id
        elif existing.user_type == UserType.CUSTOMER:
            existing.user_type, existing.role_id = UserType.PARTNER, role.id if role else None
            store.owner_user_id = existing.id
    a.status, a.store_id, a.reviewed_at = ApplicationStatus.APPROVED, store.id, datetime.now(timezone.utc)
    body = f"Hi {a.contact_person},\n\nCongratulations — {a.business_name} has been approved as a Southern Rose {data.store_type.value}."
    if temp_pw:
        body += f"\n\nPartner portal login: {a.email}\nTemporary password: {temp_pw}\nPlease sign in and change it immediately."
    await send_email(db, a.email, "Your Southern Rose distributor application is approved", "message.html", heading="Welcome to the network", body=body)
    return store
