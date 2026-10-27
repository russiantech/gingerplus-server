import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import select

from app.api.deps import DB, require_permissions
from app.core.exceptions import Conflict, NotFound
from app.enums import Permission as P
from app.models import BlogPost, Faq, HeroSlide, Page, Recipe, SiteSetting, Testimonial
from app.schemas.common import Message
from app.schemas.content import (BlogIn, BlogOut, BlogUpdate, FaqIn, FaqOut, FaqUpdate, HeroSlideIn, HeroSlideOut, PageIn, PageOut, PageUpdate,
                                 RecipeIn, RecipeOut, RecipeUpdate, SettingIn, SettingOut, TestimonialIn, TestimonialOut, TestimonialUpdate)
from app.services import settings_service
from app.services.catalog_service import unique_slug
from app.services.crud import CRUDService
from ._factory import crud_router

content = Depends(require_permissions(P.CONTENT_MANAGE))
router = APIRouter(prefix="/admin/content", tags=["admin:content"], dependencies=[content])


# ---- site settings ----
@router.get("/settings")
async def get_settings(db: DB):
    return await settings_service.all_settings(db, public_only=False)


@router.put("/settings/{key}", dependencies=[Depends(require_permissions(P.SETTINGS_MANAGE))])
async def put_setting(key: str, data: SettingIn, db: DB):
    if key not in settings_service.DEFAULTS:
        raise NotFound("Unknown setting group.")
    row = await settings_service.set_setting(db, key, data.value, data.is_public)
    return SettingOut.model_validate(row)


# ---- pages ----
pages = CRUDService(Page, "Page")


@router.get("/pages", response_model=list[PageOut])
async def list_pages(db: DB):
    return await pages.all(db, Page.title)


@router.post("/pages", response_model=PageOut, status_code=201)
async def create_page(data: PageIn, db: DB):
    if (await db.execute(select(Page.id).where(Page.slug == data.slug))).first():
        raise Conflict("A page with this slug already exists.")
    return await pages.create(db, data)


@router.get("/pages/{page_id}", response_model=PageOut)
async def get_page(page_id: uuid.UUID, db: DB):
    return await pages.get(db, page_id)


@router.patch("/pages/{page_id}", response_model=PageOut)
async def update_page(page_id: uuid.UUID, data: PageUpdate, db: DB):
    return await pages.update(db, await pages.get(db, page_id), data)


@router.delete("/pages/{page_id}", response_model=Message)
async def delete_page(page_id: uuid.UUID, db: DB):
    await pages.delete(db, await pages.get(db, page_id))
    return Message(detail="Page deleted")


# ---- blog ----
blog = CRUDService(BlogPost, "Post")


@router.get("/blog", response_model=list[BlogOut])
async def list_blog(db: DB):
    return await blog.all(db, BlogPost.created_at.desc())


@router.post("/blog", response_model=BlogOut, status_code=201)
async def create_post(data: BlogIn, db: DB):
    payload = data.model_dump(exclude={"slug"})
    payload["published_at"] = data.published_at or datetime.now(timezone.utc)
    return await blog.create(db, payload, slug=await unique_slug(db, BlogPost, data.slug or data.title))


@router.patch("/blog/{pid}", response_model=BlogOut)
async def update_post(pid: uuid.UUID, data: BlogUpdate, db: DB):
    obj = await blog.get(db, pid)
    patch = data.model_dump(exclude_unset=True)
    if patch.get("slug"):
        patch["slug"] = await unique_slug(db, BlogPost, patch["slug"], exclude=pid)
    return await blog.update(db, obj, patch)


@router.delete("/blog/{pid}", response_model=Message)
async def delete_post(pid: uuid.UUID, db: DB):
    await blog.delete(db, await blog.get(db, pid))
    return Message(detail="Post deleted")


# ---- recipes ----
recipes = CRUDService(Recipe, "Recipe")


@router.get("/recipes", response_model=list[RecipeOut])
async def list_recipes(db: DB):
    return await recipes.all(db, Recipe.sort_order, Recipe.title)


@router.post("/recipes", response_model=RecipeOut, status_code=201)
async def create_recipe(data: RecipeIn, db: DB):
    return await recipes.create(db, data.model_dump(exclude={"slug"}), slug=await unique_slug(db, Recipe, data.slug or data.title))


@router.patch("/recipes/{rid}", response_model=RecipeOut)
async def update_recipe(rid: uuid.UUID, data: RecipeUpdate, db: DB):
    obj = await recipes.get(db, rid)
    patch = data.model_dump(exclude_unset=True)
    if patch.get("slug"):
        patch["slug"] = await unique_slug(db, Recipe, patch["slug"], exclude=rid)
    return await recipes.update(db, obj, patch)


@router.delete("/recipes/{rid}", response_model=Message)
async def delete_recipe(rid: uuid.UUID, db: DB):
    await recipes.delete(db, await recipes.get(db, rid))
    return Message(detail="Recipe deleted")


# ---- simple resources via factory ----
router.include_router(crud_router(prefix="/hero", tag="hero", model=HeroSlide, label="Slide", perm=P.CONTENT_MANAGE, create=HeroSlideIn,
                                  update=HeroSlideIn, out=HeroSlideOut, order_by=lambda: (HeroSlide.sort_order,)))
router.include_router(crud_router(prefix="/testimonials", tag="testimonials", model=Testimonial, label="Testimonial", perm=P.CONTENT_MANAGE,
                                  create=TestimonialIn, update=TestimonialUpdate, out=TestimonialOut, order_by=lambda: (Testimonial.status, Testimonial.sort_order)))
router.include_router(crud_router(prefix="/faqs", tag="faqs", model=Faq, label="FAQ", perm=P.CONTENT_MANAGE, create=FaqIn, update=FaqUpdate,
                                  out=FaqOut, order_by=lambda: (Faq.group, Faq.sort_order)))
