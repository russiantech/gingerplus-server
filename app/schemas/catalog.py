import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.enums import DiscountType
from app.schemas.common import ORM, Money


class CategoryIn(BaseModel):
    name: str
    slug: str | None = None
    description: str | None = None
    image_url: str | None = None
    parent_id: uuid.UUID | None = None
    sort_order: int = 0
    is_active: bool = True


class CategoryOut(ORM):
    id: uuid.UUID
    name: str
    slug: str
    description: str | None
    image_url: str | None
    parent_id: uuid.UUID | None
    sort_order: int
    is_active: bool


class PriceTierIn(BaseModel):
    min_qty: int = Field(ge=2)
    price: Decimal = Field(ge=0)
    label: str | None = None


class PriceTierOut(ORM):
    id: uuid.UUID
    min_qty: int
    price: Money
    label: str | None


class VariantIn(BaseModel):
    id: uuid.UUID | None = None
    sku: str
    label: str
    size_label: str | None = None
    unit_count: int = 1
    pack_equivalent: Decimal = Decimal("1")
    price: Decimal = Field(ge=0)
    compare_at_price: Decimal | None = None
    stock: int = 0
    track_stock: bool = True
    is_active: bool = True
    sort_order: int = 0
    image_url: str | None = None
    tiers: list[PriceTierIn] = []


class VariantOut(ORM):
    id: uuid.UUID
    product_id: uuid.UUID
    sku: str
    label: str
    size_label: str | None
    unit_count: int
    pack_equivalent: Money
    price: Money
    compare_at_price: Money | None
    stock: int
    track_stock: bool
    is_active: bool
    sort_order: int
    image_url: str | None
    tiers: list[PriceTierOut] = []
    # computed (promotion-aware) – filled by the pricing service
    effective_price: float | None = None
    promo_label: str | None = None
    in_stock: bool = True


class ProductIn(BaseModel):
    name: str
    slug: str | None = None
    category_id: uuid.UUID | None = None
    flavor: str | None = None
    tagline: str | None = None
    short_description: str | None = None
    description: str | None = None
    benefits: list[str] = []
    ingredients: str | None = None
    nutrition: dict = {}
    how_to_enjoy: list[str] = []
    storage: str | None = None
    accent_color: str | None = None
    images: list[str] = []
    attributes: dict = {}
    is_featured: bool = False
    is_active: bool = True
    sort_order: int = 0
    meta_title: str | None = None
    meta_description: str | None = None
    variants: list[VariantIn] = []


class ProductUpdate(BaseModel):
    name: str | None = None
    slug: str | None = None
    category_id: uuid.UUID | None = None
    flavor: str | None = None
    tagline: str | None = None
    short_description: str | None = None
    description: str | None = None
    benefits: list[str] | None = None
    ingredients: str | None = None
    nutrition: dict | None = None
    how_to_enjoy: list[str] | None = None
    storage: str | None = None
    accent_color: str | None = None
    images: list[str] | None = None
    attributes: dict | None = None
    is_featured: bool | None = None
    is_active: bool | None = None
    sort_order: int | None = None
    meta_title: str | None = None
    meta_description: str | None = None
    variants: list[VariantIn] | None = None  # when provided, variants are synced (upsert by id/sku, remove missing)


class ProductOut(ORM):
    id: uuid.UUID
    name: str
    slug: str
    category_id: uuid.UUID | None
    category: CategoryOut | None = None
    flavor: str | None
    tagline: str | None
    short_description: str | None
    description: str | None
    benefits: list
    ingredients: str | None
    nutrition: dict
    how_to_enjoy: list
    storage: str | None
    accent_color: str | None
    images: list
    attributes: dict
    is_featured: bool
    is_active: bool
    sort_order: int
    meta_title: str | None
    meta_description: str | None
    variants: list[VariantOut] = []
    created_at: datetime


class PromotionIn(BaseModel):
    name: str
    code: str | None = None
    description: str | None = None
    discount_type: DiscountType = DiscountType.PERCENT
    value: Decimal = Field(gt=0)
    min_subtotal: Decimal | None = None
    max_discount: Decimal | None = None
    product_ids: list[uuid.UUID] = []
    category_ids: list[uuid.UUID] = []
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    usage_limit: int | None = None
    banner_text: str | None = None
    show_banner: bool = False
    is_active: bool = True


class PromotionUpdate(BaseModel):
    name: str | None = None
    code: str | None = None
    description: str | None = None
    discount_type: DiscountType | None = None
    value: Decimal | None = None
    min_subtotal: Decimal | None = None
    max_discount: Decimal | None = None
    product_ids: list[uuid.UUID] | None = None
    category_ids: list[uuid.UUID] | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    usage_limit: int | None = None
    banner_text: str | None = None
    show_banner: bool | None = None
    is_active: bool | None = None


class PromotionOut(ORM):
    id: uuid.UUID
    name: str
    code: str | None
    description: str | None
    discount_type: DiscountType
    value: Money
    min_subtotal: Money | None
    max_discount: Money | None
    product_ids: list
    category_ids: list
    starts_at: datetime | None
    ends_at: datetime | None
    usage_limit: int | None
    used_count: int
    banner_text: str | None
    show_banner: bool
    is_active: bool
    created_at: datetime


class StockAdjust(BaseModel):
    stock: int = Field(ge=0)
