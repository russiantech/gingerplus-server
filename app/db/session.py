from typing import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings

_kwargs = {} if settings.DATABASE_URL.startswith("sqlite") else {"pool_size": 10, "max_overflow": 20, "pool_pre_ping": True}
engine = create_async_engine(settings.DATABASE_URL, echo=False, **_kwargs)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_db() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
