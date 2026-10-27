import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Query
from sqlalchemy import or_, select

from app.api.deps import DB
from app.models import Category, Product, Promotion
from app.schemas.catalog import CategoryOut, ProductOut, PromotionOut
from app.services import catalog_service
from app.services.pricing_service import promo_active

router = APIRouter(prefix="/catalog", tags=["catalog"])


@router.get("/categories", response_model=list[CategoryOut])
async def categories(db: DB):
    return (await db.execute(select(Category).where(Category.is_active.is_(True)).order_by(Category.sort_order, Category.name))).scalars().all()


@router.get("/products", response_model=list[ProductOut])
async def products(db: DB, category: str | None = None, flavor: str | None = None, q: str | None = None, featured: bool | None = None,
                   limit: int = Query(60, le=200)):
    stmt = select(Product).where(Product.is_active.is_(True))
    if category:
        stmt = stmt.join(Category, Product.category_id == Category.id).where(Category.slug == category)
    if flavor:
        stmt = stmt.where(Product.flavor == flavor)
    if featured is not None:
        stmt = stmt.where(Product.is_featured.is_(featured))
    if q:
        like = f"%{q}%"
        stmt = stmt.where(or_(Product.name.ilike(like), Product.short_description.ilike(like)))
    rows = list((await db.execute(stmt.order_by(Product.sort_order, Product.name).limit(limit))).unique().scalars().all())
    return await catalog_service.decorate_prices(db, rows)


@router.get("/products/{slug}", response_model=ProductOut)
async def product(slug: str, db: DB):
    p = await catalog_service.get_product(db, slug, only_active=True)
    await catalog_service.decorate_prices(db, [p])
    p.variants = [v for v in p.variants if v.is_active]
    return p


@router.get("/promotions/banners", response_model=list[PromotionOut])
async def banners(db: DB):
    rows = (await db.execute(select(Promotion).where(Promotion.is_active.is_(True), Promotion.show_banner.is_(True)))).scalars().all()
    return [p for p in rows if promo_active(p)]
