import uuid
from datetime import datetime
from decimal import Decimal
from typing import Annotated, Generic, Sequence, TypeVar

from pydantic import BaseModel, ConfigDict, PlainSerializer

T = TypeVar("T")

# Money is serialised as a JSON number (float) for the client.
Money = Annotated[Decimal, PlainSerializer(lambda v: float(v), return_type=float, when_used="json")]


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class Message(BaseModel):
    detail: str


class Page(BaseModel, Generic[T]):
    items: Sequence[T]
    total: int
    page: int
    page_size: int
    pages: int


class IdModel(ORM):
    id: uuid.UUID
    created_at: datetime
