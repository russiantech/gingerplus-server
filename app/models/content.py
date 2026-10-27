import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, Entity, enum_col
from app.enums import ContentStatus, RecipeCategory


class SiteSetting(Entity, Base):
    __tablename__ = "site_settings"

    key: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    value: Mapped[dict] = mapped_column(JSON, default=dict)
    is_public: Mapped[bool] = mapped_column(Boolean, default=True)


class HeroSlide(Entity, Base):
    __tablename__ = "hero_slides"

    eyebrow: Mapped[str | None] = mapped_column(String(120))
    title: Mapped[str] = mapped_column(String(255))
    subtitle: Mapped[str | None] = mapped_column(Text)
    image_url: Mapped[str | None] = mapped_column(String(500))
    accent_color: Mapped[str | None] = mapped_column(String(20))
    primary_label: Mapped[str | None] = mapped_column(String(60))
    primary_url: Mapped[str | None] = mapped_column(String(300))
    secondary_label: Mapped[str | None] = mapped_column(String(60))
    secondary_url: Mapped[str | None] = mapped_column(String(300))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class Page(Entity, Base):
    """CMS page: ordered list of typed blocks rendered by the storefront."""
    __tablename__ = "pages"

    slug: Mapped[str] = mapped_column(String(160), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(255))
    subtitle: Mapped[str | None] = mapped_column(Text)
    banner_image_url: Mapped[str | None] = mapped_column(String(500))
    blocks: Mapped[list] = mapped_column(JSON, default=list)
    status: Mapped[ContentStatus] = mapped_column(enum_col(ContentStatus), default=ContentStatus.PUBLISHED)
    meta_title: Mapped[str | None] = mapped_column(String(255))
    meta_description: Mapped[str | None] = mapped_column(String(500))
    show_in_footer: Mapped[bool] = mapped_column(Boolean, default=False)


class BlogPost(Entity, Base):
    __tablename__ = "blog_posts"

    title: Mapped[str] = mapped_column(String(255))
    slug: Mapped[str] = mapped_column(String(280), unique=True, index=True)
    category: Mapped[str] = mapped_column(String(60), default="Recipes", index=True)
    excerpt: Mapped[str | None] = mapped_column(Text)
    body: Mapped[str] = mapped_column(Text, default="")
    cover_image_url: Mapped[str | None] = mapped_column(String(500))
    author: Mapped[str | None] = mapped_column(String(120))
    is_featured: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[ContentStatus] = mapped_column(enum_col(ContentStatus), default=ContentStatus.PUBLISHED, index=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Recipe(Entity, Base):
    __tablename__ = "recipes"

    title: Mapped[str] = mapped_column(String(200))
    slug: Mapped[str] = mapped_column(String(220), unique=True, index=True)
    category: Mapped[RecipeCategory] = mapped_column(enum_col(RecipeCategory), index=True)
    summary: Mapped[str | None] = mapped_column(String(500))
    ingredients: Mapped[list] = mapped_column(JSON, default=list)
    steps: Mapped[list] = mapped_column(JSON, default=list)
    image_url: Mapped[str | None] = mapped_column(String(500))
    featured_flavor: Mapped[str | None] = mapped_column(String(50))
    status: Mapped[ContentStatus] = mapped_column(enum_col(ContentStatus), default=ContentStatus.PUBLISHED)
    submitted_by: Mapped[str | None] = mapped_column(String(150))  # public recipe submissions arrive as drafts
    sort_order: Mapped[int] = mapped_column(Integer, default=0)


class Testimonial(Entity, Base):
    __tablename__ = "testimonials"

    author_name: Mapped[str] = mapped_column(String(150))
    author_role: Mapped[str | None] = mapped_column(String(150))  # "Bar Owner — Lagos"
    business: Mapped[str | None] = mapped_column(String(200))
    quote: Mapped[str] = mapped_column(Text)
    rating: Mapped[int] = mapped_column(Integer, default=5)
    image_url: Mapped[str | None] = mapped_column(String(500))
    status: Mapped[ContentStatus] = mapped_column(enum_col(ContentStatus), default=ContentStatus.PUBLISHED, index=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)


class Faq(Entity, Base):
    __tablename__ = "faqs"

    question: Mapped[str] = mapped_column(String(500))
    answer: Mapped[str] = mapped_column(Text)
    group: Mapped[str] = mapped_column(String(80), default="General")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
