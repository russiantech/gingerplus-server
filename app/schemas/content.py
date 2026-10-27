import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.enums import ContentStatus, RecipeCategory
from app.schemas.common import ORM


class SettingIn(BaseModel):
    value: dict
    is_public: bool = True


class SettingOut(ORM):
    key: str
    value: dict
    is_public: bool


class HeroSlideIn(BaseModel):
    eyebrow: str | None = None
    title: str
    subtitle: str | None = None
    image_url: str | None = None
    accent_color: str | None = None
    primary_label: str | None = None
    primary_url: str | None = None
    secondary_label: str | None = None
    secondary_url: str | None = None
    sort_order: int = 0
    is_active: bool = True


class HeroSlideOut(ORM, HeroSlideIn):
    id: uuid.UUID


class PageIn(BaseModel):
    slug: str
    title: str
    subtitle: str | None = None
    banner_image_url: str | None = None
    blocks: list[dict] = []
    status: ContentStatus = ContentStatus.PUBLISHED
    meta_title: str | None = None
    meta_description: str | None = None
    show_in_footer: bool = False


class PageUpdate(BaseModel):
    title: str | None = None
    subtitle: str | None = None
    banner_image_url: str | None = None
    blocks: list[dict] | None = None
    status: ContentStatus | None = None
    meta_title: str | None = None
    meta_description: str | None = None
    show_in_footer: bool | None = None


class PageOut(ORM, PageIn):
    id: uuid.UUID
    updated_at: datetime


class BlogIn(BaseModel):
    title: str
    slug: str | None = None
    category: str = "Recipes"
    excerpt: str | None = None
    body: str = ""
    cover_image_url: str | None = None
    author: str | None = None
    is_featured: bool = False
    status: ContentStatus = ContentStatus.PUBLISHED
    published_at: datetime | None = None


class BlogUpdate(BaseModel):
    title: str | None = None
    slug: str | None = None
    category: str | None = None
    excerpt: str | None = None
    body: str | None = None
    cover_image_url: str | None = None
    author: str | None = None
    is_featured: bool | None = None
    status: ContentStatus | None = None
    published_at: datetime | None = None


class BlogOut(ORM):
    id: uuid.UUID
    title: str
    slug: str
    category: str
    excerpt: str | None
    body: str
    cover_image_url: str | None
    author: str | None
    is_featured: bool
    status: ContentStatus
    published_at: datetime | None
    created_at: datetime


class RecipeIn(BaseModel):
    title: str
    slug: str | None = None
    category: RecipeCategory
    summary: str | None = None
    ingredients: list[str] = []
    steps: list[str] = []
    image_url: str | None = None
    featured_flavor: str | None = None
    status: ContentStatus = ContentStatus.PUBLISHED
    sort_order: int = 0


class RecipeUpdate(BaseModel):
    title: str | None = None
    slug: str | None = None
    category: RecipeCategory | None = None
    summary: str | None = None
    ingredients: list[str] | None = None
    steps: list[str] | None = None
    image_url: str | None = None
    featured_flavor: str | None = None
    status: ContentStatus | None = None
    sort_order: int | None = None


class RecipeOut(ORM):
    id: uuid.UUID
    title: str
    slug: str
    category: RecipeCategory
    summary: str | None
    ingredients: list
    steps: list
    image_url: str | None
    featured_flavor: str | None
    status: ContentStatus
    submitted_by: str | None
    sort_order: int


class RecipeSubmission(BaseModel):
    submitted_by: str = Field(min_length=2)
    email: str
    title: str = Field(min_length=3)
    category: RecipeCategory = RecipeCategory.COCKTAIL
    ingredients: list[str] = Field(min_length=1)
    steps: list[str] = Field(min_length=1)


class TestimonialIn(BaseModel):
    author_name: str
    author_role: str | None = None
    business: str | None = None
    quote: str
    rating: int = Field(default=5, ge=1, le=5)
    image_url: str | None = None
    status: ContentStatus = ContentStatus.PUBLISHED
    sort_order: int = 0


class TestimonialUpdate(BaseModel):
    author_name: str | None = None
    author_role: str | None = None
    business: str | None = None
    quote: str | None = None
    rating: int | None = Field(default=None, ge=1, le=5)
    image_url: str | None = None
    status: ContentStatus | None = None
    sort_order: int | None = None


class TestimonialOut(ORM):
    id: uuid.UUID
    author_name: str
    author_role: str | None
    business: str | None
    quote: str
    rating: int
    image_url: str | None
    status: ContentStatus
    sort_order: int


class ReviewSubmission(BaseModel):
    author_name: str = Field(min_length=2)
    author_role: str | None = None
    quote: str = Field(min_length=10, max_length=1500)
    rating: int = Field(default=5, ge=1, le=5)


class FaqIn(BaseModel):
    question: str
    answer: str
    group: str = "General"
    sort_order: int = 0
    is_active: bool = True


class FaqUpdate(BaseModel):
    question: str | None = None
    answer: str | None = None
    group: str | None = None
    sort_order: int | None = None
    is_active: bool | None = None


class FaqOut(ORM, FaqIn):
    id: uuid.UUID
