from datetime import datetime, timezone

from fastapi import APIRouter, Query
from sqlalchemy import select

from app.api.deps import DB
from app.core.exceptions import NotFound
from app.enums import ContentStatus, RecipeCategory
from app.models import BlogPost, Faq, HeroSlide, Page, Promotion, Recipe, Testimonial
from app.schemas.common import Message
from app.schemas.content import (BlogOut, FaqOut, HeroSlideOut, PageOut, RecipeOut, RecipeSubmission, ReviewSubmission, TestimonialOut)
from app.services import settings_service
from app.services.catalog_service import unique_slug
from app.services.email_service import notify_admin
from app.services.pricing_service import promo_active

router = APIRouter(prefix="/content", tags=["content"])
PUB = ContentStatus.PUBLISHED


@router.get("/bootstrap")
async def bootstrap(db: DB):
    """One call to initialise the storefront shell: settings, hero slides, footer pages, promo banners."""
    hero = (await db.execute(select(HeroSlide).where(HeroSlide.is_active.is_(True)).order_by(HeroSlide.sort_order))).scalars().all()
    pages = (await db.execute(select(Page).where(Page.status == PUB, Page.show_in_footer.is_(True)).order_by(Page.title))).scalars().all()
    promos = [p for p in (await db.execute(select(Promotion).where(Promotion.is_active.is_(True), Promotion.show_banner.is_(True)))).scalars().all() if promo_active(p)]
    return {
        "settings": await settings_service.all_settings(db),
        "hero": [HeroSlideOut.model_validate(h) for h in hero],
        "footer_pages": [{"slug": p.slug, "title": p.title} for p in pages],
        "banners": [{"id": str(p.id), "text": p.banner_text or p.name, "code": p.code} for p in promos],
    }


@router.get("/hero", response_model=list[HeroSlideOut])
async def hero(db: DB):
    return (await db.execute(select(HeroSlide).where(HeroSlide.is_active.is_(True)).order_by(HeroSlide.sort_order))).scalars().all()


@router.get("/pages/{slug}", response_model=PageOut)
async def page(slug: str, db: DB):
    p = (await db.execute(select(Page).where(Page.slug == slug, Page.status == PUB))).scalar_one_or_none()
    if not p:
        raise NotFound("Page not found.")
    return p


@router.get("/blog", response_model=list[BlogOut])
async def blog(db: DB, category: str | None = None, limit: int = Query(30, le=100)):
    q = select(BlogPost).where(BlogPost.status == PUB)
    if category:
        q = q.where(BlogPost.category == category)
    return (await db.execute(q.order_by(BlogPost.is_featured.desc(), BlogPost.published_at.desc()).limit(limit))).scalars().all()


@router.get("/blog/{slug}", response_model=BlogOut)
async def blog_post(slug: str, db: DB):
    p = (await db.execute(select(BlogPost).where(BlogPost.slug == slug, BlogPost.status == PUB))).scalar_one_or_none()
    if not p:
        raise NotFound("Post not found.")
    return p


@router.get("/recipes", response_model=list[RecipeOut])
async def recipes(db: DB, category: RecipeCategory | None = None):
    q = select(Recipe).where(Recipe.status == PUB)
    if category:
        q = q.where(Recipe.category == category)
    return (await db.execute(q.order_by(Recipe.sort_order, Recipe.title))).scalars().all()


@router.get("/recipes/{slug}", response_model=RecipeOut)
async def recipe(slug: str, db: DB):
    r = (await db.execute(select(Recipe).where(Recipe.slug == slug, Recipe.status == PUB))).scalar_one_or_none()
    if not r:
        raise NotFound("Recipe not found.")
    return r


@router.post("/recipes/submit", response_model=Message, status_code=201)
async def submit_recipe(data: RecipeSubmission, db: DB):
    r = Recipe(title=data.title, slug=await unique_slug(db, Recipe, data.title), category=data.category, ingredients=data.ingredients,
               steps=data.steps, status=ContentStatus.DRAFT, submitted_by=f"{data.submitted_by} <{data.email}>")
    db.add(r)
    await notify_admin(db, f"Recipe submitted: {data.title}", f"By {data.submitted_by} ({data.email}). Review it in Admin → Content → Recipes.")
    return Message(detail="Thanks! We'll review your recipe and feature it if it's a hit.")


@router.get("/testimonials", response_model=list[TestimonialOut])
async def testimonials(db: DB):
    return (await db.execute(select(Testimonial).where(Testimonial.status == PUB).order_by(Testimonial.sort_order))).scalars().all()


@router.post("/reviews", response_model=Message, status_code=201)
async def submit_review(data: ReviewSubmission, db: DB):
    db.add(Testimonial(author_name=data.author_name, author_role=data.author_role, quote=data.quote, rating=data.rating, status=ContentStatus.DRAFT))
    await notify_admin(db, "New review awaiting approval", f"{data.author_name}: {data.quote}")
    return Message(detail="Thank you! Your review will appear once approved.")


@router.get("/faqs", response_model=list[FaqOut])
async def faqs(db: DB):
    return (await db.execute(select(Faq).where(Faq.is_active.is_(True)).order_by(Faq.group, Faq.sort_order))).scalars().all()
