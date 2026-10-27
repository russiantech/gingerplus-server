# from typing import AsyncIterator

# from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# from app.core.config import settings

# _kwargs = {} if settings.DATABASE_URL.startswith("sqlite") else {"pool_size": 10, "max_overflow": 20, "pool_pre_ping": True}
# engine = create_async_engine(settings.DATABASE_URL, echo=False, **_kwargs)
# SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


# async def get_db() -> AsyncIterator[AsyncSession]:
#     async with SessionLocal() as session:
#         try:
#             yield session
#             await session.commit()
#         except Exception:
#             await session.rollback()
#             raise


#
""" 
session.py with the changes. The old pool_size=10, max_overflow=20 is what exhausted the session pooler: each Vercel instance could open up to 30 connections.
"""
import os
from typing import AsyncIterator
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings

_url = settings.DATABASE_URL
_is_sqlite = _url.startswith("sqlite")
_on_vercel = bool(os.getenv("VERCEL"))

if _is_sqlite:
    _kwargs = {}
elif _on_vercel or ":6543" in _url:
    # Supabase transaction pooler (pgbouncer): no SQLAlchemy pooling, no prepared statement cache
    _kwargs = {
        "poolclass": NullPool,
        "connect_args": {
            "statement_cache_size": 0,
            "prepared_statement_cache_size": 0,
            "prepared_statement_name_func": lambda: f"__asyncpg_{uuid4()}__",
        },
    }
else:
    # Local dev / session pooler: small pool
    _kwargs = {"pool_size": 3, "max_overflow": 2, "pool_pre_ping": True}

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
