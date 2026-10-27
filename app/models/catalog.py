import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, Entity, enum_col
from app.enums import DiscountType, ContentStatus


class Category(Entity, Base):
    __tablename__ = "categories"

    name: Mapped[str] = mapped_column(String(120))
    slug: Mapped[str] = mapped_column(String(140), unique=True, index=True)
    description: Mapped[str | None] = mapped_column(Text)
    image_url: Mapped[str | None] = mapped_column(String(500))
    parent_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("categories.id", ondelete="SET NULL"))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    products: Mapped[list["Product"]] = relationship(back_populates="category")


class Product(Entity, Base):
    """A product line (e.g. Ginger Plus with Turmeric). Sizes/packs live in ProductVariant."""
    __tablename__ = "products"

    name: Mapped[str] = mapped_column(String(200))
    slug: Mapped[str] = mapped_column(String(220), unique=True, index=True)
    category_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("categories.id", ondelete="SET NULL"), index=True)
    flavor: Mapped[str | None] = mapped_column(String(50), index=True)  # turmeric | honey | guarana
    tagline: Mapped[str | None] = mapped_column(String(255))
    short_description: Mapped[str | None] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    benefits: Mapped[list] = mapped_column(JSON, default=list)
    ingredients: Mapped[str | None] = mapped_column(Text)
    nutrition: Mapped[dict] = mapped_column(JSON, default=dict)
    how_to_enjoy: Mapped[list] = mapped_column(JSON, default=list)
    storage: Mapped[str | None] = mapped_column(Text)
    accent_color: Mapped[str | None] = mapped_column(String(20))
    images: Mapped[list] = mapped_column(JSON, default=list)  # list of URLs; first = primary
    attributes: Mapped[dict] = mapped_column(JSON, default=dict)  # free-form for future categories
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    meta_title: Mapped[str | None] = mapped_column(String(255))
    meta_description: Mapped[str | None] = mapped_column(String(500))

    category: Mapped[Category | None] = relationship(back_populates="products", lazy="joined")
    variants: Mapped[list["ProductVariant"]] = relationship(
        back_populates="product", cascade="all, delete-orphan", order_by="ProductVariant.sort_order", lazy="selectin"
    )


class ProductVariant(Entity, Base):
    """Sellable unit: a *pack* (e.g. 350ml x 24)."""
    __tablename__ = "product_variants"
    __table_args__ = (UniqueConstraint("sku", name="uq_variant_sku"),)

    product_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("products.id", ondelete="CASCADE"), index=True)
    sku: Mapped[str] = mapped_column(String(64), index=True)
    label: Mapped[str] = mapped_column(String(120))            # "350ml · Pack of 24"
    size_label: Mapped[str | None] = mapped_column(String(30))  # "350ml"
    unit_count: Mapped[int] = mapped_column(Integer, default=1)  # bottles per pack
    pack_equivalent: Mapped[Decimal] = mapped_column(Numeric(6, 2), default=1)  # how many "packs" this counts as (for the 5-pack rule)
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    compare_at_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    stock: Mapped[int] = mapped_column(Integer, default=0)
    track_stock: Mapped[bool] = mapped_column(Boolean, default=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    image_url: Mapped[str | None] = mapped_column(String(500))

    product: Mapped[Product] = relationship(back_populates="variants")
    tiers: Mapped[list["PriceTier"]] = relationship(
        back_populates="variant", cascade="all, delete-orphan", order_by="PriceTier.min_qty", lazy="selectin"
    )


class PriceTier(Entity, Base):
    """Wholesale / volume pricing: from min_qty packs, unit price becomes `price`."""
    __tablename__ = "price_tiers"

    variant_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("product_variants.id", ondelete="CASCADE"), index=True)
    min_qty: Mapped[int] = mapped_column(Integer)
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    label: Mapped[str | None] = mapped_column(String(80))

    variant: Mapped[ProductVariant] = relationship(back_populates="tiers")


class Promotion(Entity, Base):
    __tablename__ = "promotions"

    name: Mapped[str] = mapped_column(String(150))
    code: Mapped[str | None] = mapped_column(String(40), unique=True, index=True)  # null => automatic promotion
    description: Mapped[str | None] = mapped_column(String(500))
    discount_type: Mapped[DiscountType] = mapped_column(enum_col(DiscountType), default=DiscountType.PERCENT)
    value: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    min_subtotal: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    max_discount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    product_ids: Mapped[list] = mapped_column(JSON, default=list)   # empty => all products
    category_ids: Mapped[list] = mapped_column(JSON, default=list)
    starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    usage_limit: Mapped[int | None] = mapped_column(Integer)
    used_count: Mapped[int] = mapped_column(Integer, default=0)
    banner_text: Mapped[str | None] = mapped_column(String(255))  # shown on storefront when active
    show_banner: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
