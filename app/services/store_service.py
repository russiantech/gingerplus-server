import re
import uuid

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.enums import StoreStatus
from app.models import Store
from app.utils.geo import haversine_km
from app.utils.slug import slugify


async def unique_store_slug(db: AsyncSession, name: str, exclude: uuid.UUID | None = None) -> str:
    base = slugify(name)
    slug, n = base, 1
    while True:
        q = select(Store.id).where(Store.slug == slug)
        if exclude:
            q = q.where(Store.id != exclude)
        if not (await db.execute(q)).first():
            return slug
        n += 1
        slug = f"{base}-{n}"


async def nearest_store(db: AsyncSession, *, state: str | None, lat: float | None = None, lng: float | None = None,
                        public_only: bool = True, limit: int = 1) -> list[tuple[Store, float | None]]:
    """Closest approved store. Uses coordinates when available, otherwise state / coverage match."""
    q = select(Store).where(Store.status == StoreStatus.APPROVED)
    if public_only:
        q = q.where(Store.is_public.is_(True))
    stores = (await db.execute(q)).scalars().all()
    scored: list[tuple[Store, float | None, int]] = []
    for s in stores:
        dist = None
        if lat is not None and lng is not None and s.latitude is not None and s.longitude is not None:
            dist = haversine_km(lat, lng, s.latitude, s.longitude)
        same_state = bool(state) and (s.state.lower() == state.lower() or state.lower() in [c.lower() for c in (s.coverage_states or [])])
        if dist is None and not same_state:
            continue
        # rank: same-state first, then distance
        scored.append((s, dist, 0 if same_state else 1))
    scored.sort(key=lambda t: (t[2], t[1] if t[1] is not None else 1e9))
    return [(s, d) for s, d, _ in scored[:limit]]
