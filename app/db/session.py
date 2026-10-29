import os
from uuid import uuid4
from typing import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings

_url = settings.DATABASE_URL
_pooled = any(x in _url for x in ("pooler.", ":6543", "pgbouncer"))  # Supabase/Neon/PgBouncer transaction pooling
_serverless = settings.DB_NULL_POOL or bool(os.getenv("VERCEL"))
if _url.startswith("sqlite"):
    _kwargs: dict = {}
elif _serverless or _pooled:
    # Serverless / pgbouncer (transaction mode): no long-lived pool, and no *named* prepared statements. SQLAlchemy names them
    # "__asyncpg_stmt_N__", which collide across pooled server connections — so each gets a unique name and the caches are off.
    _kwargs = {"connect_args": {"statement_cache_size": 0, "prepared_statement_cache_size": 0, "timeout": 10,
                                "prepared_statement_name_func": lambda: f"__asyncpg_{uuid4()}__"}}
    if _serverless:
        _kwargs["poolclass"] = NullPool
    else:
        _kwargs.update(pool_size=5, max_overflow=10, pool_pre_ping=True, pool_recycle=300)
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
