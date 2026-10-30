import uuid

from sqlalchemy import String, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import Conflict, NotFound
from app.models import Category, PriceTier, Product, ProductVariant
from app.schemas.catalog import ProductIn, ProductUpdate, VariantIn
from app.services.pricing_service import active_auto_promotions, best_auto_promo, tier_price
from app.utils.slug import slugify


async def unique_slug(db: AsyncSession, model, base: str, exclude: uuid.UUID | None = None) -> str:
    base = slugify(base)
    slug, n = base, 1
    while True:
        q = select(model.id).where(model.slug == slug)
        if exclude:
            q = q.where(model.id != exclude)
        if not (await db.execute(q)).first():
            return slug
        n += 1
        slug = f"{base}-{n}"


async def get_product(db: AsyncSession, ident: str | uuid.UUID, *, only_active: bool = False) -> Product:
    cond = Product.id == ident if isinstance(ident, uuid.UUID) else Product.slug == ident
    q = select(Product).where(cond)
    if only_active:
        q = q.where(Product.is_active.is_(True))
    p = (await db.execute(q)).unique().scalar_one_or_none()
    if not p:
        raise NotFound("Product not found.")
    return p


def _apply_variant(v: ProductVariant, d: VariantIn) -> None:
    for f in ("sku", "label", "size_label", "unit_count", "pack_equivalent", "price", "compare_at_price", "stock", "track_stock",
              "is_active", "sort_order", "image_url"):
        setattr(v, f, getattr(d, f))
    v.tiers = [PriceTier(min_qty=t.min_qty, price=t.price, label=t.label) for t in d.tiers]


async def _sync_variants(db: AsyncSession, product: Product, items: list[VariantIn]) -> None:
    existing = {v.id: v for v in product.variants}
    by_sku = {v.sku: v for v in product.variants}
    keep: set[uuid.UUID] = set()
    for d in items:
        v = existing.get(d.id) if d.id else by_sku.get(d.sku)
        if v is None:
            clash = (await db.execute(select(ProductVariant.id).where(ProductVariant.sku == d.sku))).first()
            if clash:
                raise Conflict(f"SKU {d.sku} is already in use.", code="sku_taken")
            v = ProductVariant(product_id=product.id)
            product.variants.append(v)
        _apply_variant(v, d)
        keep.add(v.id)
    for v in list(product.variants):
        if v.id not in keep and v.id in existing:
            product.variants.remove(v)


def _all_images(product: Product) -> list[str]:
    return [u for u in [*(product.images or []), *(v.image_url for v in product.variants)] if u]


async def release_images(db: AsyncSession, urls: set[str]) -> None:
    """Delete files that were removed from a product, but only if they live in our storage and nothing else still uses them."""
    from app.core.storage import delete_by_url
    for u in urls:
        still = (await db.execute(select(Product.id).where(Product.images.cast(String).contains(u)).limit(1))).first() or \
                (await db.execute(select(ProductVariant.id).where(ProductVariant.image_url == u).limit(1))).first()
        if not still:
            await delete_by_url(u)


async def _reload(db: AsyncSession, product_id: uuid.UUID) -> Product:
    """Re-read with every relationship eagerly loaded: serialising a product must never trigger lazy IO (MissingGreenlet)."""
    q = (select(Product).where(Product.id == product_id).options(selectinload(Product.variants).selectinload(ProductVariant.tiers))
         .execution_options(populate_existing=True))
    return (await db.execute(q)).unique().scalar_one()


async def create_product(db: AsyncSession, data: ProductIn) -> Product:
    payload = data.model_dump(exclude={"variants", "slug"})
    product = Product(**payload, slug=await unique_slug(db, Product, data.slug or data.name))
    db.add(product)
    await db.flush()
    await _sync_variants(db, product, data.variants)
    await db.flush()
    return await _reload(db, product.id)


async def update_product(db: AsyncSession, product: Product, data: ProductUpdate) -> Product:
    patch = data.model_dump(exclude_unset=True, exclude={"variants", "slug"})
    old_images = set(_all_images(product))
    for k, v in patch.items():
        setattr(product, k, v)
    if data.slug:
        product.slug = await unique_slug(db, Product, data.slug, exclude=product.id)
    if data.variants is not None:
        await _sync_variants(db, product, data.variants)
    await db.flush()
    product = await _reload(db, product.id)
    await release_images(db, old_images - set(_all_images(product)))
    return product


async def decorate_prices(db: AsyncSession, products: list[Product]):
    """Attach promotion-aware effective prices to variants (transient attrs read by schema)."""
    autos = await active_auto_promotions(db)
    for p in products:
        for v in p.variants:
            for v2 in [v]:
                v2.product = p  # ensure relationship for promo scope check
            promo, off = best_auto_promo(autos, v, v.price)
            v.effective_price = float(v.price - off)
            v.promo_label = promo.name if promo else None
            v.in_stock = (not v.track_stock) or v.stock > 0
    return products
