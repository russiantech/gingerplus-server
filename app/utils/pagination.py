from math import ceil
from typing import Generic, Sequence, TypeVar

from fastapi import Query
from pydantic import BaseModel
from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

T = TypeVar("T")


class PageParams:
    def __init__(self, page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100)):
        self.page, self.page_size = page, page_size

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


class Paginated(BaseModel, Generic[T]):
    items: Sequence[T]
    total: int
    page: int
    page_size: int
    pages: int


async def paginate(db: AsyncSession, stmt: Select, params: PageParams, unique: bool = False):
    """Returns (rows, total, pages). `stmt` must select a single entity."""
    count_stmt = select(func.count()).select_from(stmt.order_by(None).subquery())
    total = (await db.execute(count_stmt)).scalar_one()
    res = await db.execute(stmt.limit(params.page_size).offset(params.offset))
    rows = res.unique().scalars().all() if unique else res.scalars().all()
    return rows, total, max(1, ceil(total / params.page_size))


def page_of(rows, total, pages, params: PageParams) -> dict:
    return {"items": rows, "total": total, "page": params.page, "page_size": params.page_size, "pages": pages}
