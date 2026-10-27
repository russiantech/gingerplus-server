import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from app.enums import UserType
from app.schemas.auth import UserOut
from app.schemas.common import ORM


class AdminUserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    first_name: str
    last_name: str = ""
    phone: str | None = None
    role_key: str
    user_type: UserType = UserType.STAFF


class AdminUserUpdate(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    phone: str | None = None
    role_key: str | None = None
    user_type: UserType | None = None
    is_active: bool | None = None
    linked_store_id: uuid.UUID | None = None
    notes: str | None = None
    password: str | None = Field(default=None, min_length=8)


class CustomerListItem(UserOut):
    order_count: int = 0
    total_spent: float = 0
    notes: str | None = None


class RoleCreate(BaseModel):
    key: str = Field(pattern=r"^[a-z][a-z0-9_]{2,48}$")
    name: str
    description: str = ""
    permissions: list[str] = []


class RoleUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    permissions: list[str] | None = None


class AddressIn(BaseModel):
    label: str = "Home"
    recipient_name: str
    phone: str
    line1: str
    line2: str | None = None
    city: str
    state: str
    lga: str | None = None
    country: str = "Nigeria"
    latitude: float | None = None
    longitude: float | None = None
    is_default: bool = False


class AddressUpdate(BaseModel):
    label: str | None = None
    recipient_name: str | None = None
    phone: str | None = None
    line1: str | None = None
    line2: str | None = None
    city: str | None = None
    state: str | None = None
    lga: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    is_default: bool | None = None


class AddressOut(ORM, AddressIn):
    id: uuid.UUID
