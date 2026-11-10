"""Async SQLAlchemy engine, session factory and table creation."""

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from job_filter.core.config import settings


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


engine: AsyncEngine = create_async_engine(settings.database_url)
async_session_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
    engine, expire_on_commit=False
)


async def get_session() -> AsyncIterator[AsyncSession]:
    """Yield one session per request and close it afterwards."""
    async with async_session_factory() as session:
        yield session


async def init_db(target: AsyncEngine) -> None:
    """Create all tables that do not exist yet (no migrations)."""
    # Import so JobRow is registered on Base.metadata before create_all.
    from job_filter.core import models  # noqa: F401

    async with target.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
