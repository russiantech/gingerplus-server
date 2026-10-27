"""Router factory for simple admin CRUD resources."""
import uuid
from typing import Callable, Type

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select

from app.api.deps import DB, require_permissions
from app.enums import Permission
from app.schemas.common import Message
from app.services.crud import CRUDService


def crud_router(*, prefix: str, tag: str, model, label: str, perm: Permission, create: Type[BaseModel], update: Type[BaseModel],
                out: Type[BaseModel], order_by: Callable | None = None, before_create: Callable | None = None) -> APIRouter:
    r = APIRouter(prefix=prefix, tags=[f"admin:{tag}"], dependencies=[Depends(require_permissions(perm))])
    svc = CRUDService(model, label)

    @r.get("", response_model=list[out])
    async def list_(db: DB):
        order = order_by() if order_by else ()
        return await svc.all(db, *order)

    @r.post("", response_model=out, status_code=201)
    async def create_(data: create, db: DB):  # type: ignore[valid-type]
        payload = data.model_dump()
        if before_create:
            payload = await before_create(db, payload)
        return await svc.create(db, payload)

    @r.get("/{item_id}", response_model=out)
    async def get_(item_id: uuid.UUID, db: DB):
        return await svc.get(db, item_id)

    @r.patch("/{item_id}", response_model=out)
    async def update_(item_id: uuid.UUID, data: update, db: DB):  # type: ignore[valid-type]
        return await svc.update(db, await svc.get(db, item_id), data)

    @r.delete("/{item_id}", response_model=Message)
    async def delete_(item_id: uuid.UUID, db: DB):
        await svc.delete(db, await svc.get(db, item_id))
        return Message(detail=f"{label} deleted")

    return r
