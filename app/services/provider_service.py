"""Payment provider configuration & resolution.

Resolution order for credentials of a provider:
  1. Admin-saved row in `payment_providers` (enabled, with a secret)  → source "database"
  2. Environment variables (PAYSTACK_* / FLUTTERWAVE_*)               → source "environment"
If the admin explicitly disabled a provider it is off (no env fallback) — disabling is an intentional switch-off.
Which *online* gateway handles a new payment: explicit default → first enabled provider → env DEFAULT_ONLINE_PROVIDER →
any env-configured provider → the dev mock (non-production only).
"""
import logging
import uuid

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import crypto
from app.core.config import settings
from app.core.exceptions import AppError, NotFound, PaymentError
from app.models import PaymentProviderConfig
from app.services.gateways.base import Credentials, Gateway
from app.services.gateways.flutterwave import FlutterwaveGateway
from app.services.gateways.mock import MockGateway
from app.services.gateways.paystack import PaystackGateway

log = logging.getLogger(__name__)

ONLINE = {"paystack": PaystackGateway, "flutterwave": FlutterwaveGateway}
CATALOG = {
    "paystack": {"name": "Paystack", "kind": "online", "blurb": "Cards, bank transfer and USSD in an in-page popup."},
    "flutterwave": {"name": "Flutterwave", "kind": "online", "blurb": "Cards, bank transfer and mobile money via inline checkout."},
    "bank_transfer": {"name": "Bank transfer", "kind": "offline", "blurb": "Account details shown to customers who choose to pay by transfer."},
}
BANK_FIELDS = ("bank_name", "account_name", "account_number", "instructions")


def _env_creds(provider: str) -> Credentials | None:
    if provider == "paystack" and settings.PAYSTACK_SECRET_KEY:
        k = settings.PAYSTACK_SECRET_KEY
        return Credentials("paystack", k, settings.PAYSTACK_PUBLIC_KEY, "", "live" if k.startswith("sk_live") else "test", "environment", settings.PAYSTACK_BASE_URL)
    if provider == "flutterwave" and settings.FLUTTERWAVE_SECRET_KEY:
        k = settings.FLUTTERWAVE_SECRET_KEY
        return Credentials("flutterwave", k, settings.FLUTTERWAVE_PUBLIC_KEY, settings.FLUTTERWAVE_WEBHOOK_SECRET, "test" if "TEST" in k.upper() else "live", "environment", settings.FLUTTERWAVE_BASE_URL)
    return None


async def get_row(db: AsyncSession, provider: str) -> PaymentProviderConfig | None:
    return (await db.execute(select(PaymentProviderConfig).where(PaymentProviderConfig.provider == provider))).scalar_one_or_none()


def _db_creds(row: PaymentProviderConfig) -> Credentials | None:
    secret = crypto.decrypt(row.secret_key_enc)
    if not secret:
        return None
    base = settings.PAYSTACK_BASE_URL if row.provider == "paystack" else settings.FLUTTERWAVE_BASE_URL
    return Credentials(row.provider, secret, row.public_key or "", crypto.decrypt(row.webhook_secret_enc) or "", row.mode, "database", base, row.extra or {})


async def load_credentials(db: AsyncSession, provider: str) -> Credentials | None:
    row = await get_row(db, provider)
    if row is not None:
        if not row.is_enabled:
            return None
        creds = _db_creds(row)
        if creds:
            return creds
    return _env_creds(provider)


def _mock_allowed() -> bool:
    return not settings.is_production


async def gateway_for(db: AsyncSession, provider: str) -> Gateway:
    """Gateway for an existing payment (verify / webhook / admin confirm) — must use the same provider that created it."""
    if provider == "mock":
        return MockGateway()
    cls = ONLINE.get(provider)
    creds = await load_credentials(db, provider) if cls else None
    if not cls or not creds:
        raise PaymentError(f"{CATALOG.get(provider, {}).get('name', provider)} is not configured. Add its keys in Admin → Payment settings.", code="gateway_not_configured")
    return cls(creds)


async def active_online_gateway(db: AsyncSession) -> Gateway:
    rows = {r.provider: r for r in (await db.execute(select(PaymentProviderConfig).where(PaymentProviderConfig.provider.in_(list(ONLINE))))).scalars()}
    order: list[str] = []
    default_row = next((r.provider for r in rows.values() if r.is_default and r.is_enabled), None)
    if default_row:
        order.append(default_row)
    order += [p for p in ONLINE if p in rows and rows[p].is_enabled and p not in order]
    if settings.DEFAULT_ONLINE_PROVIDER in ONLINE and settings.DEFAULT_ONLINE_PROVIDER not in order:
        order.append(settings.DEFAULT_ONLINE_PROVIDER)
    order += [p for p in ONLINE if p not in order]
    for p in order:
        creds = await load_credentials(db, p)
        if creds:
            return ONLINE[p](creds)
    if _mock_allowed():
        return MockGateway()
    raise PaymentError("Online payments are not available right now. Please pay by bank transfer or contact us on WhatsApp.", code="gateway_not_configured")


async def public_config(db: AsyncSession) -> dict:
    """What the storefront needs to know: is online payment available, which provider, and the bank-transfer details."""
    try:
        gw = await active_online_gateway(db)
        online = {"available": True, "provider": gw.name, "mock": gw.name == "mock"}
    except PaymentError:
        online = {"available": False, "provider": None, "mock": False}
    bank = await get_row(db, "bank_transfer")
    bank_out = None
    if bank and bank.is_enabled:
        bank_out = {k: (bank.extra or {}).get(k, "") for k in BANK_FIELDS}
    return {"online": online, "bank_transfer": bank_out}


# ---------------- admin ----------------
def _webhook_url(provider: str) -> str:
    return f"{settings.API_URL.rstrip('/')}{settings.API_V1_PREFIX}/payments/webhook/{provider}"


async def describe_all(db: AsyncSession) -> list[dict]:
    rows = {r.provider: r for r in (await db.execute(select(PaymentProviderConfig))).scalars()}
    active = None
    try:
        active = (await active_online_gateway(db)).name
    except PaymentError:
        pass
    out = []
    for key, meta in CATALOG.items():
        row = rows.get(key)
        item = {"provider": key, "display_name": (row.display_name if row and row.display_name else meta["name"]), "kind": meta["kind"], "blurb": meta["blurb"],
                "is_enabled": bool(row and row.is_enabled), "is_default": bool(row and row.is_default), "mode": row.mode if row else "test",
                "public_key": row.public_key if row else None, "has_secret": False, "secret_masked": None, "secret_fingerprint": row.secret_fingerprint if row else None,
                "has_webhook_secret": bool(row and row.webhook_secret_enc), "extra": (row.extra if row else {}) or {}, "env_available": False,
                "source": "none", "active": active == key, "webhook_url": _webhook_url(key) if meta["kind"] == "online" else None,
                "updated_at": row.updated_at if row else None, "needs_reentry": False}
        if meta["kind"] == "online":
            if row and row.secret_key_enc:
                plain = crypto.decrypt(row.secret_key_enc)
                item["has_secret"], item["secret_masked"], item["needs_reentry"] = bool(plain), crypto.mask(plain), plain is None
            item["env_available"] = _env_creds(key) is not None
            if row and row.is_enabled and item["has_secret"]:
                item["source"] = "database"
            elif not (row and not row.is_enabled) and item["env_available"]:
                item["source"] = "environment"
        out.append(item)
    return out


async def upsert(db: AsyncSession, provider: str, data: dict, actor_id: uuid.UUID | None) -> PaymentProviderConfig:
    if provider not in CATALOG:
        raise NotFound("Unknown payment provider.")
    row = await get_row(db, provider)
    if row is None:
        row = PaymentProviderConfig(provider=provider, extra={})
        db.add(row)
    if "display_name" in data:
        row.display_name = (data["display_name"] or None)
    if "is_enabled" in data and data["is_enabled"] is not None:
        row.is_enabled = data["is_enabled"]
    if data.get("mode") in ("test", "live"):
        row.mode = data["mode"]
    if "public_key" in data and data["public_key"] is not None:
        row.public_key = data["public_key"].strip() or None
    secret = (data.get("secret_key") or "").strip()
    if data.get("clear_secret"):
        row.secret_key_enc = row.secret_fingerprint = None
    elif secret:
        row.secret_key_enc, row.secret_fingerprint = crypto.encrypt(secret), crypto.fingerprint(secret)
    hook = (data.get("webhook_secret") or "").strip()
    if data.get("clear_webhook_secret"):
        row.webhook_secret_enc = None
    elif hook:
        row.webhook_secret_enc = crypto.encrypt(hook)
    if data.get("extra") is not None:
        allowed = BANK_FIELDS if provider == "bank_transfer" else ()
        row.extra = {**(row.extra or {}), **{k: str(v) for k, v in data["extra"].items() if k in allowed}}
    if CATALOG[provider]["kind"] == "online" and row.is_enabled and not (row.secret_key_enc or _env_creds(provider)):
        raise AppError("Add a secret key before enabling this provider (or set it in the server environment).", code="missing_secret")
    row.updated_by_id = actor_id
    await db.flush()
    return row


async def set_default(db: AsyncSession, provider: str) -> None:
    if provider not in ONLINE:
        raise AppError("Only online providers can be the default.", code="bad_provider")
    if not await load_credentials(db, provider):
        raise AppError("Configure and enable this provider before making it the default.", code="provider_unconfigured")
    row = await get_row(db, provider)
    if row is None:  # env-only provider: create an enabled row so the choice persists
        row = PaymentProviderConfig(provider=provider, is_enabled=True, mode=_env_creds(provider).mode, extra={})
        db.add(row)
        await db.flush()
    await db.execute(update(PaymentProviderConfig).values(is_default=False))
    row.is_default = True
    row.is_enabled = True


async def remove(db: AsyncSession, provider: str) -> None:
    row = await get_row(db, provider)
    if row:
        await db.delete(row)


async def test_connection(db: AsyncSession, provider: str) -> tuple[bool, str, str]:
    if provider not in ONLINE:
        raise AppError("Only online providers can be tested.", code="bad_provider")
    row = await get_row(db, provider)
    creds = _db_creds(row) if row and row.secret_key_enc else None
    creds = creds or _env_creds(provider)  # test what is saved even if currently disabled
    if not creds:
        return False, "No credentials saved for this provider.", "none"
    ok, msg = await ONLINE[provider](creds).test()
    return ok, msg, creds.source
