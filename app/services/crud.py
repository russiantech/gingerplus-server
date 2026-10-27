"""Small generic async CRUD helper for simple content models."""
import uuid
from typing import Generic, Type, TypeVar

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFound

M = TypeVar("M")


class CRUDService(Generic[M]):
    def __init__(self, model: Type[M], label: str = "Item"):
        self.model, self.label = model, label

    async def get(self, db: AsyncSession, id: uuid.UUID) -> M:
        obj = await db.get(self.model, id)
        if not obj:
            raise NotFound(f"{self.label} not found.")
        return obj

    async def create(self, db: AsyncSession, data: BaseModel | dict, **extra) -> M:
        payload = data if isinstance(data, dict) else data.model_dump()
        obj = self.model(**{**payload, **extra})
        db.add(obj)
        await db.flush()
        await db.refresh(obj)
        return obj

    async def update(self, db: AsyncSession, obj: M, data: BaseModel | dict) -> M:
        patch = data if isinstance(data, dict) else data.model_dump(exclude_unset=True)
        for k, v in patch.items():
            setattr(obj, k, v)
        await db.flush()
        await db.refresh(obj)
        return obj

    async def delete(self, db: AsyncSession, obj: M) -> None:
        await db.delete(obj)
        await db.flush()

    async def all(self, db: AsyncSession, *order) -> list[M]:
        q = select(self.model)
        if order:
            q = q.order_by(*order)
        return list((await db.execute(q)).scalars().all())
