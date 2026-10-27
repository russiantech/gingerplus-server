from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from urllib.parse import urlparse

from sqlalchemy import and_, case, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from user_agents import parse as parse_ua

from app.enums import OrderStatus, PaymentStatus, UserType
from app.models import Order, OrderItem, PageView, Payment, ProductVariant, User
from app.schemas.analytics import TrackEvent


def _since(days: int) -> datetime:
    return datetime.now(timezone.utc) - timedelta(days=days)


def _f(v) -> float:
    return float(v or 0)


async def track_view(db: AsyncSession, ev: TrackEvent, user_agent: str, user_id=None) -> None:
    ua = parse_ua(user_agent or "")
    host = None
    if ev.referrer:
        host = urlparse(ev.referrer).netloc or None
    device = "bot" if ua.is_bot else "mobile" if ua.is_mobile else "tablet" if ua.is_tablet else "desktop"
    db.add(PageView(session_id=ev.session_id, path=ev.path.split("?")[0][:500], referrer=ev.referrer, referrer_host=host,
                    utm_source=ev.utm_source, device=device, browser=ua.browser.family, os=ua.os.family, is_bot=ua.is_bot, user_id=user_id))


async def dashboard(db: AsyncSession, days: int = 30) -> dict:
    start, prev_start = _since(days), _since(days * 2)
    paid = Payment.status == PaymentStatus.PAID

    async def rev(a, b=None):
        c = [paid, Payment.paid_at >= a] + ([Payment.paid_at < b] if b else [])
        return _f((await db.execute(select(func.coalesce(func.sum(Payment.amount), 0)).where(*c))).scalar_one())

    async def cnt(model, *conds):
        return (await db.execute(select(func.count()).select_from(model).where(*conds))).scalar_one()

    revenue, prev_revenue = await rev(start), await rev(prev_start, start)
    orders, prev_orders = await cnt(Order, Order.created_at >= start), await cnt(Order, Order.created_at >= prev_start, Order.created_at < start)
    customers = await cnt(User, User.user_type == UserType.CUSTOMER, User.created_at >= start)
    prev_customers = await cnt(User, User.user_type == UserType.CUSTOMER, User.created_at >= prev_start, User.created_at < start)

    series_rows = (await db.execute(
        select(func.date(Order.created_at).label("d"), func.count(Order.id), func.coalesce(func.sum(Order.total), 0))
        .where(Order.created_at >= start, Order.status != OrderStatus.CANCELLED).group_by("d").order_by("d"))).all()
    pay_rows = (await db.execute(
        select(func.date(Payment.paid_at).label("d"), func.coalesce(func.sum(Payment.amount), 0)).where(paid, Payment.paid_at >= start).group_by("d"))).all()
    pay_map = {str(d): _f(v) for d, v in pay_rows}
    ord_map = {str(d): (c, _f(t)) for d, c, t in series_rows}
    series = []
    for i in range(days):
        d = str((start + timedelta(days=i + 1)).date())
        series.append({"date": d, "orders": ord_map.get(d, (0, 0))[0], "order_value": ord_map.get(d, (0, 0))[1], "revenue": pay_map.get(d, 0)})

    by_status = [{"status": s.value if hasattr(s, "value") else s, "count": c} for s, c in
                 (await db.execute(select(Order.status, func.count()).group_by(Order.status))).all()]
    by_channel = [{"channel": c.value if hasattr(c, "value") else c, "count": n, "total": _f(t)} for c, n, t in
                  (await db.execute(select(Order.channel, func.count(), func.coalesce(func.sum(Order.total), 0)).where(Order.created_at >= start).group_by(Order.channel))).all()]
    by_state = [{"state": s or "Unknown", "orders": n, "total": _f(t)} for s, n, t in
                (await db.execute(select(Order.delivery_state, func.count(), func.coalesce(func.sum(Order.total), 0))
                                  .where(Order.created_at >= start).group_by(Order.delivery_state).order_by(desc(func.count())).limit(8))).all()]
    top = (await db.execute(
        select(OrderItem.product_name, OrderItem.variant_label, func.sum(OrderItem.quantity), func.sum(OrderItem.line_total))
        .join(Order, Order.id == OrderItem.order_id).where(Order.created_at >= start, Order.status != OrderStatus.CANCELLED)
        .group_by(OrderItem.product_name, OrderItem.variant_label).order_by(desc(func.sum(OrderItem.line_total))).limit(6))).all()
    low = (await db.execute(
        select(ProductVariant.sku, ProductVariant.label, ProductVariant.stock).where(ProductVariant.track_stock.is_(True), ProductVariant.is_active.is_(True), ProductVariant.stock <= 20)
        .order_by(ProductVariant.stock).limit(8))).all()
    recent = (await db.execute(select(Order).order_by(desc(Order.created_at)).limit(8))).unique().scalars().all()

    return {
        "days": days,
        "kpis": {
            "revenue": revenue, "revenue_prev": prev_revenue, "orders": orders, "orders_prev": prev_orders,
            "new_customers": customers, "new_customers_prev": prev_customers,
            "avg_order_value": round(revenue / orders, 2) if orders else 0,
            "pending_orders": await cnt(Order, Order.status == OrderStatus.PENDING),
            "unpaid_orders": await cnt(Order, Order.payment_status.in_([PaymentStatus.UNPAID, PaymentStatus.PENDING]), Order.status != OrderStatus.CANCELLED),
            "pending_store_approvals": await cnt(Order, Order.assignment_status == "suggested"),
        },
        "series": series, "orders_by_status": by_status, "orders_by_channel": by_channel, "sales_by_state": by_state,
        "top_products": [{"name": n, "variant": v, "quantity": int(q or 0), "revenue": _f(r)} for n, v, q, r in top],
        "low_stock": [{"sku": s, "label": l, "stock": st} for s, l, st in low],
        "recent_orders": [{"id": str(o.id), "number": o.number, "customer": o.customer_name, "total": _f(o.total), "status": o.status.value,
                           "payment_status": o.payment_status.value, "created_at": o.created_at.isoformat()} for o in recent],
    }


async def traffic(db: AsyncSession, days: int = 30) -> dict:
    start = _since(days)
    base = [PageView.created_at >= start, PageView.is_bot.is_(False)]
    total = (await db.execute(select(func.count()).where(*base))).scalar_one()
    sessions = (await db.execute(select(func.count(func.distinct(PageView.session_id))).where(*base))).scalar_one()
    rows = (await db.execute(select(func.date(PageView.created_at).label("d"), func.count(), func.count(func.distinct(PageView.session_id)))
                             .where(*base).group_by("d").order_by("d"))).all()
    m = {str(d): (v, s) for d, v, s in rows}
    series = [{"date": str((start + timedelta(days=i + 1)).date()), "views": m.get(str((start + timedelta(days=i + 1)).date()), (0, 0))[0],
               "visitors": m.get(str((start + timedelta(days=i + 1)).date()), (0, 0))[1]} for i in range(days)]

    async def top(col, limit=8):
        r = (await db.execute(select(col, func.count()).where(*base, col.is_not(None)).group_by(col).order_by(desc(func.count())).limit(limit))).all()
        return [{"label": a, "count": b} for a, b in r]

    bounce = (await db.execute(select(func.count()).select_from(
        select(PageView.session_id).where(*base).group_by(PageView.session_id).having(func.count() == 1).subquery()))).scalar_one()
    return {"days": days, "page_views": total, "visitors": sessions, "bounce_rate": round(bounce / sessions * 100, 1) if sessions else 0,
            "series": series, "top_pages": await top(PageView.path), "referrers": await top(PageView.referrer_host),
            "devices": await top(PageView.device), "browsers": await top(PageView.browser)}
