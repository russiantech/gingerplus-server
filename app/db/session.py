import os
from typing import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings

_url = settings.DATABASE_URL
_serverless = settings.DB_NULL_POOL or bool(os.getenv("VERCEL"))
if _url.startswith("sqlite"):
    _kwargs: dict = {}
elif _serverless:
    # Serverless: no long-lived pool; disable asyncpg's prepared-statement cache so Supabase/pgbouncer poolers work.
    _kwargs = {"poolclass": NullPool, "connect_args": {"statement_cache_size": 0, "prepared_statement_cache_size": 0, "timeout": 10}}
else:
    _kwargs = {"pool_size": 10, "max_overflow": 20, "pool_pre_ping": True, "pool_recycle": 1800, "pool_timeout": 15, "connect_args": {"timeout": 10}}
engine = create_async_engine(_url, echo=False, **_kwargs)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_db() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
