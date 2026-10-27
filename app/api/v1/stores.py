from fastapi import APIRouter, Query
from sqlalchemy import select

from app.api.deps import DB
from app.core.exceptions import Conflict
from app.enums import ApplicationStatus, StoreStatus
from app.models import DistributorApplication, Store
from app.schemas.common import Message
from app.schemas.store import StorePublic, StoreSignup, SuggestStoreOut
from app.services import store_service
from app.services.email_service import notify_admin, send_email
from app.utils.geo import NIGERIAN_STATES
from app.utils.text import normalize_email, normalize_phone

router = APIRouter(prefix="/stores", tags=["stores"])


@router.get("/states", response_model=list[str])
async def states():
    return NIGERIAN_STATES


@router.get("", response_model=list[StorePublic])
async def list_public(db: DB, state: str | None = None):
    q = select(Store).where(Store.status == StoreStatus.APPROVED, Store.is_public.is_(True))
    if state:
        q = q.where(Store.state.ilike(state))
    return (await db.execute(q.order_by(Store.state, Store.name))).scalars().all()


@router.get("/nearest", response_model=SuggestStoreOut)
async def nearest(db: DB, state: str | None = None, lat: float | None = Query(None), lng: float | None = Query(None)):
    """Find the closest public store/dealer for a visitor (by coordinates, else by state)."""
    found = await store_service.nearest_store(db, state=state, lat=lat, lng=lng, public_only=True)
    if not found:
        return SuggestStoreOut(store=None, reason="No dealer in your area yet — contact us on WhatsApp and we'll deliver directly.")
    store, dist = found[0]
    out = StorePublic.model_validate(store)
    out.distance_km = round(dist, 1) if dist is not None else None
    return SuggestStoreOut(store=out, reason="Closest dealer to your location" if dist is not None else f"Dealer serving {store.state}")


@router.post("/signup", response_model=Message, status_code=201)
async def signup(data: StoreSignup, db: DB):
    """Public 'Become a distributor' application (Section 12 form)."""
    email = normalize_email(data.email)
    dup = (await db.execute(select(DistributorApplication.id).where(
        DistributorApplication.email == email, DistributorApplication.status.in_([ApplicationStatus.NEW, ApplicationStatus.REVIEWING])))).first()
    if dup:
        raise Conflict("You already have an application under review. We'll be in touch within 5 working days.", code="application_exists")
    app_ = DistributorApplication(**{**data.model_dump(), "email": email, "phone": normalize_phone(data.phone)})
    db.add(app_)
    await db.flush()
    await send_email(db, email, "We received your distributor application", "message.html", heading="Application received",
                     body=f"Hi {data.contact_person},\n\nThank you for applying to become a Southern Rose distributor. We review applications within 5 working days, then schedule a call to discuss terms.\n\n— Southern Rose Team")
    await notify_admin(db, f"New distributor application: {data.business_name}",
                       f"{data.contact_person} · {data.phone} · {email}\n{data.location}\nExpected volume: {data.expected_monthly_volume}\n\n{data.motivation or ''}")
    return Message(detail="Application received. We review within 5 working days.")
