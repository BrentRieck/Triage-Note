import os
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase


DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./app.db")


def _sync_url(url: str) -> str:
    if url.startswith("sqlite+aiosqlite"):
        return url.replace("sqlite+aiosqlite", "sqlite", 1)
    if url.startswith("postgresql+asyncpg"):
        return url.replace("+asyncpg", "", 1)
    return url


ASYNC_DATABASE_URL = DATABASE_URL
SYNC_DATABASE_URL = _sync_url(DATABASE_URL)

engine = create_async_engine(ASYNC_DATABASE_URL, echo=False, future=True)
async_session_maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


class Base(DeclarativeBase):
    pass


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session


__all__ = [
    "DATABASE_URL",
    "ASYNC_DATABASE_URL",
    "SYNC_DATABASE_URL",
    "engine",
    "async_session_maker",
    "get_session",
    "Base",
]
