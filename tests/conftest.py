import os

os.environ.update(DATABASE_URL="sqlite+aiosqlite:///./test.db", EMAIL_ENABLED="false", ENVIRONMENT="development", PAYSTACK_SECRET_KEY="")

import fakeredis.aioredis
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.core import redis as redis_mod
from app.db.base import Base
from app.db.init_db import seed_all
from app.db.session import engine
import app.models  # noqa: F401
from app.main import app


@pytest_asyncio.fixture
async def client():
    redis_mod.set_redis(fakeredis.aioredis.FakeRedis(decode_responses=True))
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    await seed_all()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
