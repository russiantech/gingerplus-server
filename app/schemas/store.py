import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from app.enums import ApplicationStatus, StoreStatus, StoreType
from app.schemas.common import ORM


class StoreIn(BaseModel):
    name: str
    store_type: StoreType = StoreType.STORE
    status: StoreStatus = StoreStatus.APPROVED
    is_public: bool = True
    owner_user_id: uuid.UUID | None = None
    contact_person: str | None = None
    phone: str | None = None
    whatsapp: str | None = None
    email: EmailStr | None = None
    address: str
    city: str | None = None
    state: str
    lga: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    coverage_states: list[str] = []
    opening_hours: str | None = None
    image_url: str | None = None
    notes: str | None = None


class StoreUpdate(BaseModel):
    name: str | None = None
    store_type: StoreType | None = None
    status: StoreStatus | None = None
    is_public: bool | None = None
    owner_user_id: uuid.UUID | None = None
    contact_person: str | None = None
    phone: str | None = None
    whatsapp: str | None = None
    email: EmailStr | None = None
    address: str | None = None
    city: str | None = None
    state: str | None = None
    lga: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    coverage_states: list[str] | None = None
    opening_hours: str | None = None
    image_url: str | None = None
    notes: str | None = None


class StorePublic(ORM):
    id: uuid.UUID
    name: str
    slug: str
    store_type: StoreType
    phone: str | None
    whatsapp: str | None
    email: str | None
    address: str
    city: str | None
    state: str
    latitude: float | None
    longitude: float | None
    coverage_states: list
    opening_hours: str | None
    image_url: str | None
    distance_km: float | None = None


class StoreOut(StorePublic):
    status: StoreStatus
    is_public: bool
    owner_user_id: uuid.UUID | None
    contact_person: str | None
    lga: str | None
    notes: str | None
    created_at: datetime


class StoreSignup(BaseModel):
    """A store/distributor owner signing up (creates a pending store + account application)."""
    business_name: str
    contact_person: str
    phone: str
    email: EmailStr
    location: str
    state: str | None = None
    years_in_distribution: int | None = Field(default=None, ge=0, le=80)
    current_products: str | None = None
    expected_monthly_volume: int | None = Field(default=None, ge=0)
    motivation: str | None = None


class ApplicationOut(ORM):
    id: uuid.UUID
    business_name: str
    contact_person: str
    phone: str
    email: EmailStr
    location: str
    state: str | None
    years_in_distribution: int | None
    current_products: str | None
    expected_monthly_volume: int | None
    motivation: str | None
    status: ApplicationStatus
    admin_notes: str | None
    store_id: uuid.UUID | None
    created_at: datetime


class ApplicationUpdate(BaseModel):
    status: ApplicationStatus | None = None
    admin_notes: str | None = None


class ApproveApplication(BaseModel):
    store_type: StoreType = StoreType.DISTRIBUTOR
    is_public: bool = False
    address: str | None = None
    state: str | None = None
    city: str | None = None
    create_partner_account: bool = True


class SuggestStoreOut(BaseModel):
    store: StorePublic | None
    reason: str
