import os
from collections.abc import AsyncGenerator

from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase


DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./app.db")


def _sync_url(url: str) -> str:
    """Return a synchronous SQLAlchemy URL for Alembic operations.

    Alembic expects a synchronous driver. Our application might be configured
    with async drivers such as ``sqlite+aiosqlite`` or ``postgresql+asyncpg``.
    ``sqlalchemy.engine.make_url`` lets us safely parse any URL and drop the
    ``+driver`` suffix regardless of the specific async driver that is used.
    This avoids ``ModuleNotFoundError`` crashes when Alembic tries to import a
    driver that only exists for the async runtime (e.g. ``postgresql+propongo``).
    """

    try:
        parsed = make_url(url)
    except Exception:  # pragma: no cover - defensive guard for malformed URLs
        return url

    drivername = parsed.drivername
    if "+" not in drivername:
        return url

    dialect, _, _ = drivername.partition("+")
    sync_url = parsed.set(drivername=dialect)
    return sync_url.render_as_string(hide_password=False)


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
