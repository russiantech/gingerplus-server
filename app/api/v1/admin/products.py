import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_, select

from app.api.deps import DB, require_permissions
from app.core.exceptions import Conflict
from app.enums import Permission as P
from app.models import Category, OrderItem, Product, ProductVariant, Promotion
from app.schemas.catalog import (CategoryIn, CategoryOut, ProductIn, ProductOut, ProductUpdate, PromotionIn, PromotionOut, PromotionUpdate,
                                 StockAdjust, VariantOut)
from app.schemas.common import Message, Page
from app.services import catalog_service
from app.services.crud import CRUDService
from app.utils.pagination import PageParams, page_of, paginate

router = APIRouter(prefix="/admin", tags=["admin:catalog"])
view, manage, promo = (Depends(require_permissions(P.PRODUCTS_VIEW, P.PRODUCTS_MANAGE, any_of=True)), Depends(require_permissions(P.PRODUCTS_MANAGE)),
                       Depends(require_permissions(P.PROMOTIONS_MANAGE)))


@router.get("/products", response_model=Page[ProductOut], dependencies=[view])
async def list_products(db: DB, params: PageParams = Depends(), q: str | None = None, category_id: uuid.UUID | None = None, active: bool | None = None):
    stmt = select(Product)
    if q:
        stmt = stmt.where(or_(Product.name.ilike(f"%{q}%"), Product.slug.ilike(f"%{q}%")))
    if category_id:
        stmt = stmt.where(Product.category_id == category_id)
    if active is not None:
        stmt = stmt.where(Product.is_active.is_(active))
    rows, total, pages = await paginate(db, stmt.order_by(Product.sort_order, Product.name), params, unique=True)
    return page_of(rows, total, pages, params)


@router.post("/products", response_model=ProductOut, status_code=201, dependencies=[manage])
async def create_product(data: ProductIn, db: DB):
    return await catalog_service.create_product(db, data)


@router.get("/products/{product_id}", response_model=ProductOut, dependencies=[view])
async def get_product(product_id: uuid.UUID, db: DB):
    return await catalog_service.get_product(db, product_id)


@router.patch("/products/{product_id}", response_model=ProductOut, dependencies=[manage])
async def update_product(product_id: uuid.UUID, data: ProductUpdate, db: DB):
    return await catalog_service.update_product(db, await catalog_service.get_product(db, product_id), data)


@router.delete("/products/{product_id}", response_model=Message, dependencies=[manage])
async def delete_product(product_id: uuid.UUID, db: DB):
    p = await catalog_service.get_product(db, product_id)
    used = (await db.execute(select(func.count()).select_from(OrderItem).where(OrderItem.product_id == p.id))).scalar_one()
    if used:  # keep history intact: archive instead
        p.is_active = False
        return Message(detail="Product has order history, so it was archived (hidden) instead of deleted.")
    await db.delete(p)
    return Message(detail="Product deleted")


@router.patch("/variants/{variant_id}/stock", response_model=VariantOut, dependencies=[manage])
async def set_stock(variant_id: uuid.UUID, data: StockAdjust, db: DB):
    v = await db.get(ProductVariant, variant_id)
    if not v:
        from app.core.exceptions import NotFound
        raise NotFound("Variant not found.")
    v.stock = data.stock
    return v


# ---- categories ----
cats = CRUDService(Category, "Category")


@router.get("/categories", response_model=list[CategoryOut], dependencies=[view])
async def list_categories(db: DB):
    return await cats.all(db, Category.sort_order, Category.name)


@router.post("/categories", response_model=CategoryOut, status_code=201, dependencies=[manage])
async def create_category(data: CategoryIn, db: DB):
    payload = data.model_dump(exclude={"slug"})
    return await cats.create(db, payload, slug=await catalog_service.unique_slug(db, Category, data.slug or data.name))


@router.patch("/categories/{cid}", response_model=CategoryOut, dependencies=[manage])
async def update_category(cid: uuid.UUID, data: CategoryIn, db: DB):
    c = await cats.get(db, cid)
    patch = data.model_dump(exclude={"slug"})
    if data.slug:
        patch["slug"] = await catalog_service.unique_slug(db, Category, data.slug, exclude=cid)
    if data.parent_id == cid:
        raise Conflict("A category cannot be its own parent.")
    return await cats.update(db, c, patch)


@router.delete("/categories/{cid}", response_model=Message, dependencies=[manage])
async def delete_category(cid: uuid.UUID, db: DB):
    c = await cats.get(db, cid)
    if (await db.execute(select(func.count()).select_from(Product).where(Product.category_id == cid))).scalar_one():
        raise Conflict("Move or delete this category's products first.", code="category_in_use")
    await cats.delete(db, c)
    return Message(detail="Category deleted")


# ---- promotions ----
promos = CRUDService(Promotion, "Promotion")


def _promo_payload(d: dict) -> dict:
    d = dict(d)
    if "code" in d and d["code"]:
        d["code"] = d["code"].strip().upper()
    for k in ("product_ids", "category_ids"):
        if k in d and d[k] is not None:
            d[k] = [str(x) for x in d[k]]
    return d


@router.get("/promotions", response_model=list[PromotionOut], dependencies=[promo])
async def list_promotions(db: DB):
    return await promos.all(db, Promotion.created_at.desc())


@router.post("/promotions", response_model=PromotionOut, status_code=201, dependencies=[promo])
async def create_promotion(data: PromotionIn, db: DB):
    if data.code and (await db.execute(select(Promotion.id).where(Promotion.code == data.code.strip().upper()))).first():
        raise Conflict("That coupon code already exists.", code="code_taken")
    return await promos.create(db, _promo_payload(data.model_dump()))


@router.patch("/promotions/{pid}", response_model=PromotionOut, dependencies=[promo])
async def update_promotion(pid: uuid.UUID, data: PromotionUpdate, db: DB):
    return await promos.update(db, await promos.get(db, pid), _promo_payload(data.model_dump(exclude_unset=True)))


@router.delete("/promotions/{pid}", response_model=Message, dependencies=[promo])
async def delete_promotion(pid: uuid.UUID, db: DB):
    await promos.delete(db, await promos.get(db, pid))
    return Message(detail="Promotion deleted")
