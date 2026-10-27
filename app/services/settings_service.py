from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models import SiteSetting

DEFAULTS: dict[str, dict] = {
    "brand": {
        "name": "Southern Rose", "product_line": "Ginger Plus", "slogan": "Pursuing wellbeing",
        "taglines": ["Bold Ginger. Three Powerful Blends.", "Bold Ginger. Perfect Plus.", "Real Ingredients. Real Benefits."],
    },
    "contact": {
        "email": "southernrose.enueshike@gmail.com", "press_email": "nolpartnership2015@gmail.com",
        "phone": "+2349035483698", "phone_hours": "Mon–Fri, 8am–6pm",
        "whatsapp_numbers": ["+2348027724193", "+2349035483698"],
        "address": "29, Losoro Dr. Fish, Lakowe School Gate, Ibeju Lekki, Lagos",
        "maps_url": "https://maps.google.com/?q=Lakowe+School+Gate+Ibeju+Lekki+Lagos",
    },
    "social": {"instagram": "https://instagram.com/gingerplus_biorefinery", "facebook": "https://facebook.com/gingerplus_biorefinery",
               "tiktok": "https://tiktok.com/@gingerplus_biorefinery", "handle": "@gingerplus_biorefinery"},
    "commerce": {
        "online_payment_max_packs": settings.ONLINE_PAYMENT_MAX_PACKS,
        "allow_online_wholesale": True,
        "wholesale_min_packs": 20,
        "auto_suggest_store": False,
        "bank_details": "Bank transfer details available on request — message us on WhatsApp.",
        "default_delivery_fee": settings.DEFAULT_DELIVERY_FEE,
        "free_delivery_over": None,
        "currency": "NGN",
    },
    "announcement": {"enabled": False, "text": ""},
}


async def get_setting(db: AsyncSession, key: str) -> dict:
    row = (await db.execute(select(SiteSetting).where(SiteSetting.key == key))).scalar_one_or_none()
    base = dict(DEFAULTS.get(key, {}))
    if row:
        base.update(row.value or {})
    return base


async def all_settings(db: AsyncSession, public_only: bool = True) -> dict[str, dict]:
    rows = {r.key: r for r in (await db.execute(select(SiteSetting))).scalars().all()}
    out: dict[str, dict] = {}
    for key, default in DEFAULTS.items():
        row = rows.get(key)
        if row and public_only and not row.is_public:
            continue
        merged = dict(default)
        if row:
            merged.update(row.value or {})
        out[key] = merged
    if public_only:
        out.get("commerce", {}).pop("bank_details", None)  # shown only at checkout when relevant
    return out


async def set_setting(db: AsyncSession, key: str, value: dict, is_public: bool = True) -> SiteSetting:
    row = (await db.execute(select(SiteSetting).where(SiteSetting.key == key))).scalar_one_or_none()
    if row:
        row.value = {**(row.value or {}), **value}
        row.is_public = is_public
    else:
        row = SiteSetting(key=key, value=value, is_public=is_public)
        db.add(row)
    await db.flush()
    return row
