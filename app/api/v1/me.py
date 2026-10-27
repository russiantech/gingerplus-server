import uuid

from fastapi import APIRouter
from sqlalchemy import select

from app.api.deps import DB, CurrentUser
from app.core.exceptions import NotFound
from app.models import Address, Store
from app.schemas.auth import ProfileUpdate, UserOut
from app.schemas.common import Message
from app.schemas.store import StorePublic
from app.schemas.user import AddressIn, AddressOut, AddressUpdate
from app.utils.text import normalize_phone

router = APIRouter(prefix="/me", tags=["account"])


@router.get("", response_model=UserOut)
async def me(user: CurrentUser):
    return user


@router.patch("", response_model=UserOut)
async def update_me(data: ProfileUpdate, user: CurrentUser):
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(user, k, normalize_phone(v) if k == "phone" else v)
    return user


@router.get("/store", response_model=StorePublic | None)
async def my_linked_store(db: DB, user: CurrentUser):
    return await db.get(Store, user.linked_store_id) if user.linked_store_id else None


async def _unset_defaults(db, user_id):
    for a in (await db.execute(select(Address).where(Address.user_id == user_id))).scalars():
        a.is_default = False


@router.get("/addresses", response_model=list[AddressOut])
async def list_addresses(db: DB, user: CurrentUser):
    rows = (await db.execute(select(Address).where(Address.user_id == user.id).order_by(Address.is_default.desc(), Address.created_at.desc()))).scalars().all()
    return rows


@router.post("/addresses", response_model=AddressOut, status_code=201)
async def add_address(data: AddressIn, db: DB, user: CurrentUser):
    has_any = (await db.execute(select(Address.id).where(Address.user_id == user.id))).first()
    if data.is_default or not has_any:
        await _unset_defaults(db, user.id)
    addr = Address(user_id=user.id, **{**data.model_dump(), "phone": normalize_phone(data.phone), "is_default": data.is_default or not has_any})
    db.add(addr)
    await db.flush()
    return addr


async def _own(db, user, address_id: uuid.UUID) -> Address:
    a = (await db.execute(select(Address).where(Address.id == address_id, Address.user_id == user.id))).scalar_one_or_none()
    if not a:
        raise NotFound("Address not found.")
    return a


@router.patch("/addresses/{address_id}", response_model=AddressOut)
async def update_address(address_id: uuid.UUID, data: AddressUpdate, db: DB, user: CurrentUser):
    a = await _own(db, user, address_id)
    patch = data.model_dump(exclude_unset=True)
    if patch.get("is_default"):
        await _unset_defaults(db, user.id)
    for k, v in patch.items():
        setattr(a, k, v)
    return a


@router.delete("/addresses/{address_id}", response_model=Message)
async def delete_address(address_id: uuid.UUID, db: DB, user: CurrentUser):
    await db.delete(await _own(db, user, address_id))
    return Message(detail="Address removed")
