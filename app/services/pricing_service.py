"""Pricing engine: tiers → automatic promotions → coupon → delivery. Single source of truth for quotes."""
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import AppError, Conflict
from app.enums import DiscountType
from app.models import ProductVariant, Promotion, ShippingRate
from app.schemas.order import CartLine, Quote, QuoteLine
from app.services.settings_service import get_setting
from app.utils.text import whatsapp_link

Q = Decimal("0.01")


def money(v) -> Decimal:
    return Decimal(v).quantize(Q, rounding=ROUND_HALF_UP)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _aware(dt: datetime | None) -> datetime | None:
    return dt.replace(tzinfo=timezone.utc) if dt and dt.tzinfo is None else dt


def promo_active(p: Promotion, now: datetime | None = None) -> bool:
    now = now or _now()
    if not p.is_active:
        return False
    if (s := _aware(p.starts_at)) and s > now:
        return False
    if (e := _aware(p.ends_at)) and e < now:
        return False
    if p.usage_limit is not None and p.used_count >= p.usage_limit:
        return False
    return True


def promo_applies(p: Promotion, variant: ProductVariant) -> bool:
    pids = {str(x) for x in (p.product_ids or [])}
    cids = {str(x) for x in (p.category_ids or [])}
    if not pids and not cids:
        return True
    if str(variant.product_id) in pids:
        return True
    return bool(variant.product.category_id and str(variant.product.category_id) in cids)


def _discount(p: Promotion, amount: Decimal) -> Decimal:
    d = amount * Decimal(p.value) / 100 if p.discount_type == DiscountType.PERCENT else Decimal(p.value)
    if p.max_discount:
        d = min(d, Decimal(p.max_discount))
    return money(min(d, amount))


@dataclass
class PricedLine:
    variant: ProductVariant
    quantity: int
    base_unit: Decimal
    unit: Decimal
    tier_label: str | None = None
    promo_label: str | None = None

    @property
    def total(self) -> Decimal:
        return money(self.unit * self.quantity)

    @property
    def packs(self) -> Decimal:
        return Decimal(self.variant.pack_equivalent) * self.quantity


@dataclass
class PricingResult:
    lines: list[PricedLine]
    subtotal: Decimal
    coupon_discount: Decimal
    delivery_fee: Decimal
    total: Decimal
    total_packs: Decimal
    coupon: Promotion | None = None
    coupon_error: str | None = None
    eta: tuple[int, int] | None = None
    commerce: dict = field(default_factory=dict)

    @property
    def is_wholesale(self) -> bool:
        return self.total_packs >= self.commerce.get("online_payment_max_packs", 5)


async def active_auto_promotions(db: AsyncSession) -> list[Promotion]:
    rows = (await db.execute(select(Promotion).where(Promotion.is_active.is_(True), Promotion.code.is_(None)))).scalars().all()
    return [p for p in rows if promo_active(p)]


def best_auto_promo(promos: list[Promotion], variant: ProductVariant, unit: Decimal):
    best, best_d = None, Decimal(0)
    for p in promos:
        if promo_applies(p, variant):
            d = _discount(p, unit)
            if d > best_d:
                best, best_d = p, d
    return best, best_d


def tier_price(variant: ProductVariant, qty: int) -> tuple[Decimal, str | None]:
    price, label = Decimal(variant.price), None
    for t in sorted(variant.tiers, key=lambda t: t.min_qty):
        if qty >= t.min_qty:
            price, label = Decimal(t.price), t.label or f"{t.min_qty}+ packs"
    return price, label


async def price_cart(db: AsyncSession, items: list[CartLine], *, state: str | None = None, coupon_code: str | None = None,
                     strict_coupon: bool = False, enforce_stock: bool = False) -> PricingResult:
    if not items:
        raise AppError("Your cart is empty.", code="empty_cart")
    merged: dict[uuid.UUID, int] = {}
    for it in items:
        merged[it.variant_id] = merged.get(it.variant_id, 0) + it.quantity
    variants = (await db.execute(
        select(ProductVariant).options(selectinload(ProductVariant.product)).where(ProductVariant.id.in_(merged.keys()))
    )).scalars().all()
    by_id = {v.id: v for v in variants}
    commerce = await get_setting(db, "commerce")
    autos = await active_auto_promotions(db)

    lines: list[PricedLine] = []
    for vid, qty in merged.items():
        v = by_id.get(vid)
        if not v or not v.is_active or not v.product.is_active:
            raise AppError("One of the items in your cart is no longer available.", code="item_unavailable")
        if enforce_stock and v.track_stock and v.stock < qty:
            raise Conflict(f"Only {v.stock} left of {v.product.name} ({v.label}).", code="insufficient_stock")
        unit, tier_label = tier_price(v, qty)
        promo, off = best_auto_promo(autos, v, unit)
        lines.append(PricedLine(v, qty, Decimal(v.price), money(unit - off), tier_label, promo.name if promo else None))

    subtotal = money(sum((l.total for l in lines), Decimal(0)))
    total_packs = sum((l.packs for l in lines), Decimal(0))

    coupon, coupon_error, coupon_discount = None, None, Decimal(0)
    if coupon_code:
        code = coupon_code.strip().upper()
        promo = (await db.execute(select(Promotion).where(Promotion.code.ilike(code)))).scalar_one_or_none()
        if not promo or not promo_active(promo):
            coupon_error = "This coupon is invalid or has expired."
        else:
            eligible = money(sum((l.total for l in lines if promo_applies(promo, l.variant)), Decimal(0)))
            if eligible <= 0:
                coupon_error = "This coupon doesn't apply to the items in your cart."
            elif promo.min_subtotal and subtotal < Decimal(promo.min_subtotal):
                coupon_error = f"Spend at least ₦{Decimal(promo.min_subtotal):,.0f} to use this coupon."
            else:
                coupon, coupon_discount = promo, _discount(promo, eligible)
    if coupon_error and strict_coupon:
        raise AppError(coupon_error, code="invalid_coupon")

    fee, eta = Decimal(commerce.get("default_delivery_fee", 0)), None
    if state:
        rate = (await db.execute(select(ShippingRate).where(ShippingRate.state.ilike(state), ShippingRate.is_active.is_(True)))).scalar_one_or_none()
        if rate:
            fee, eta = Decimal(rate.fee), (rate.eta_min_days, rate.eta_max_days)
    free_over = commerce.get("free_delivery_over")
    if free_over and subtotal - coupon_discount >= Decimal(free_over):
        fee = Decimal(0)
    fee = money(fee)
    total = money(subtotal - coupon_discount + fee)
    return PricingResult(lines, subtotal, coupon_discount, fee, total, total_packs, coupon, coupon_error, eta, commerce)


def to_quote(r: PricingResult, whatsapp_number: str | None = None) -> Quote:
    max_packs = int(r.commerce.get("online_payment_max_packs", 5))
    allowed = (not r.is_wholesale) or bool(r.commerce.get("allow_online_wholesale", True))
    msg = "Hello Southern Rose, I'd like to order: " + ", ".join(f"{l.quantity}× {l.variant.product.name} ({l.variant.label})" for l in r.lines)
    return Quote(
        lines=[QuoteLine(
            variant_id=l.variant.id, product_name=l.variant.product.name, variant_label=l.variant.label,
            image_url=l.variant.image_url or ((l.variant.product.images or [None])[0]), quantity=l.quantity,
            base_unit_price=float(l.base_unit), unit_price=float(l.unit), line_total=float(l.total),
            tier_label=l.tier_label, promo_label=l.promo_label,
            available=(not l.variant.track_stock) or l.variant.stock >= l.quantity,
        ) for l in r.lines],
        subtotal=float(r.subtotal), discount_total=float(r.coupon_discount), delivery_fee=float(r.delivery_fee),
        total=float(r.total), total_packs=float(r.total_packs), coupon_code=r.coupon.code if r.coupon else None,
        coupon_error=r.coupon_error, promotion_name=r.coupon.name if r.coupon else None, is_wholesale=r.is_wholesale,
        online_payment_allowed=allowed, online_payment_max_packs=max_packs,
        whatsapp_url=whatsapp_link(whatsapp_number, msg) if whatsapp_number else None,
        eta_min_days=r.eta[0] if r.eta else None, eta_max_days=r.eta[1] if r.eta else None,
    )
