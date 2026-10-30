"""Idempotent seeding:  python -m app.db.init_db"""
import asyncio
import logging
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.permissions import DEFAULT_ROLES
from app.core.security import hash_password
from app.db import seed_data as D
from app.db.session import SessionLocal
from app.enums import ContentStatus, RecipeCategory, StoreStatus, StoreType, UserType
from app.models import (BlogPost, Category, Faq, HeroSlide, Page, PriceTier, Product, ProductVariant, Promotion, Recipe, Role, ShippingRate,
                        Store, Testimonial, User)
from app.utils.geo import NIGERIAN_STATES
from app.utils.slug import slugify

log = logging.getLogger(__name__)


async def seed_roles(db: AsyncSession) -> dict[str, Role]:
    roles = {}
    for key, spec in DEFAULT_ROLES.items():
        r = (await db.execute(select(Role).where(Role.key == key))).scalar_one_or_none()
        if not r:
            r = Role(key=key, name=spec["name"], description=spec["description"], permissions=spec["permissions"], is_system=True)
            db.add(r)
        elif key == "super_admin":
            r.permissions = spec["permissions"]
        roles[key] = r
    await db.flush()
    return roles


async def seed_superuser(db: AsyncSession, roles: dict[str, Role]) -> None:
    email = settings.FIRST_SUPERUSER_EMAIL.lower()
    if (await db.execute(select(User.id).where(User.email == email))).first():
        return
    db.add(User(email=email, password_hash=hash_password(settings.FIRST_SUPERUSER_PASSWORD), first_name="Southern", last_name="Admin",
                user_type=UserType.STAFF, role_id=roles["super_admin"].id, email_verified_at=datetime.now(timezone.utc)))


async def _exists(db, model, **kw) -> bool:
    q = select(model.id)
    for k, v in kw.items():
        q = q.where(getattr(model, k) == v)
    return (await db.execute(q.limit(1))).first() is not None


async def seed_catalog(db: AsyncSession) -> None:
    cats = {}
    for name, slug, desc, order in D.CATEGORIES:
        c = (await db.execute(select(Category).where(Category.slug == slug))).scalar_one_or_none()
        if not c:
            c = Category(name=name, slug=slug, description=desc, sort_order=order, is_active=slug != "merchandise")
            db.add(c)
        cats[slug] = c
    await db.flush()
    for spec in D.PRODUCTS:
        if await _exists(db, Product, slug=spec["slug"]):
            continue
        p = Product(**spec, category_id=cats["ginger-drinks"].id, images=list(D.PRODUCT_IMAGES[spec["flavor"]]))
        db.add(p)
        await db.flush()
        for s in D.SIZES:
            v = ProductVariant(product_id=p.id, sku=f"SR-GP-{spec['flavor'][:3].upper()}-{s['size'].upper()}", label=s["label"], size_label=s["size"],
                               unit_count=s["count"], pack_equivalent=Decimal(1), price=Decimal(s["price"]), stock=200, sort_order=s["sort"],
                               image_url=None)  # variants inherit the product gallery unless an admin sets their own photo
            v.tiers = [PriceTier(min_qty=s["tier"][0], price=Decimal(s["tier"][1]), label="Wholesale (20+ packs)")]
            db.add(v)


async def seed_shipping(db: AsyncSession) -> None:
    existing = {r.state for r in (await db.execute(select(ShippingRate))).scalars()}
    table = {**D.LAGOS, **D.SW, **D.REMOTE}
    for st in NIGERIAN_STATES:
        if st in existing:
            continue
        fee, lo, hi = table.get(st, (5000, 2, 5))
        db.add(ShippingRate(state=st, fee=Decimal(fee), eta_min_days=lo, eta_max_days=hi))


async def seed_content(db: AsyncSession) -> None:
    if not (await db.execute(select(HeroSlide.id).limit(1))).first():
        for h in D.HERO:
            db.add(HeroSlide(**h, image_url=None))
    for pg in D.PAGES:
        if not await _exists(db, Page, slug=pg["slug"]):
            db.add(Page(**pg, status=ContentStatus.PUBLISHED))
    if not (await db.execute(select(Faq.id).limit(1))).first():
        for i, (q, a, g) in enumerate(D.FAQS):
            db.add(Faq(question=q, answer=a, group=g, sort_order=i))
    if not (await db.execute(select(Testimonial.id).limit(1))).first():
        for i, (n, role, biz, quote) in enumerate(D.TESTIMONIALS):
            db.add(Testimonial(author_name=n, author_role=role, business=biz, quote=quote, sort_order=i))
    for i, (title, cat, flavor, summary, ings, steps) in enumerate(D.RECIPES):
        if not await _exists(db, Recipe, slug=slugify(title)):
            db.add(Recipe(title=title, slug=slugify(title), category=RecipeCategory(cat), featured_flavor=flavor, summary=summary, ingredients=ings, steps=steps, sort_order=i))
    for title, cat, featured, excerpt, body in D.BLOG:
        if not await _exists(db, BlogPost, slug=slugify(title)):
            db.add(BlogPost(title=title, slug=slugify(title), category=cat, is_featured=featured, excerpt=excerpt, body=body, author="Southern Rose Team",
                            published_at=datetime.now(timezone.utc)))
    if not await _exists(db, Store, slug="southern-rose-hq"):
        db.add(Store(name="Southern Rose HQ", slug="southern-rose-hq", store_type=StoreType.STORE, status=StoreStatus.APPROVED, is_public=True,
                     phone="+2349035483698", whatsapp="+2348027724193", email="southernrose.enueshike@gmail.com",
                     address="29, Losoro Dr. Fish, Lakowe School Gate, Ibeju Lekki", city="Ibeju Lekki", state="Lagos", latitude=6.4698, longitude=3.9469,
                     coverage_states=["Lagos", "Ogun"], opening_hours="Mon–Fri, 8am–6pm"))
    if not await _exists(db, Promotion, code="WELCOME10"):
        db.add(Promotion(name="Welcome 10%", code="WELCOME10", description="10% off your first order", value=Decimal(10), max_discount=Decimal(5000), is_active=True))


def _legacy(u: str | None) -> bool:
    return not u or (u.startswith("/images/") and u.endswith(".svg"))


async def sync_seed_images(db: AsyncSession) -> None:
    """Replace the old placeholder artwork with the real photos — only where a record still points at a placeholder, so anything an admin uploaded is never touched."""
    for p in (await db.execute(select(Product))).unique().scalars():
        if p.flavor in D.PRODUCT_IMAGES and (not p.images or all(_legacy(u) for u in p.images)):
            p.images = list(D.PRODUCT_IMAGES[p.flavor])
        for v in p.variants:
            if v.image_url and _legacy(v.image_url):
                v.image_url = None
    for i, h in enumerate((await db.execute(select(HeroSlide).order_by(HeroSlide.sort_order))).scalars()):
        if _legacy(h.image_url):
            h.image_url = D.HERO_IMAGES[i % len(D.HERO_IMAGES)]
    for pg in (await db.execute(select(Page))).scalars():
        if not pg.banner_image_url and pg.slug in D.PAGE_BANNERS:
            pg.banner_image_url = D.PAGE_BANNERS[pg.slug]
    for r in (await db.execute(select(Recipe))).scalars():
        if _legacy(r.image_url):
            r.image_url = D.FLAVOR_BANNER.get(r.featured_flavor or "", D.FLAVOR_BANNER["turmeric"])
    for i, b in enumerate((await db.execute(select(BlogPost).order_by(BlogPost.created_at))).scalars()):
        if _legacy(b.cover_image_url):
            b.cover_image_url = D.BLOG_COVERS[i % len(D.BLOG_COVERS)]


async def seed_all() -> None:
    async with SessionLocal() as db:
        roles = await seed_roles(db)
        await seed_superuser(db, roles)
        await seed_catalog(db)
        await seed_shipping(db)
        await seed_content(db)
        await db.flush()
        await sync_seed_images(db)
        await db.commit()
    log.info("Seed complete")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(seed_all())
