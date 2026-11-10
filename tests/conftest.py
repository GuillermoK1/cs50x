"""Shared pytest fixtures."""

from collections.abc import AsyncIterator, Callable
from typing import Any

import httpx
import pytest
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool

from job_filter.api.dependencies import get_detector
from job_filter.api.main import app
from job_filter.core.config import settings
from job_filter.core.database import get_session, init_db
from job_filter.core.scam_detector import ScamDetector
from job_filter.core.schemas import JobSummary


@pytest.fixture
def valid_job() -> JobSummary:
    """Return a valid normalized job offer for tests."""
    return JobSummary(
        id="example-1",
        title="Python Developer",
        company="Example Company",
        description="Build and maintain Python applications.",
        location="Remote",
        salary_min=60_000,
        salary_max=80_000,
        currency="USD",
        url="https://example.com/jobs/example-1",
        source="example",
    )

@pytest.fixture
def make_job(valid_job: JobSummary) -> Callable[..., JobSummary]:
    """Return a factory that builds valid jobs with field overrides."""

    def _make(**overrides: Any) -> JobSummary:
        return JobSummary(**(valid_job.model_dump() | overrides))

    return _make


@pytest.fixture(autouse=True)
def _no_real_keys(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch) -> None:
    """Never pick up real Adzuna keys from .env (live tests are exempt)."""
    if request.node.get_closest_marker("live"):
        return
    monkeypatch.setattr(settings, "adzuna_app_id", None)
    monkeypatch.setattr(settings, "adzuna_app_key", None)


@pytest.fixture
async def engine() -> AsyncIterator[AsyncEngine]:
    """In-memory SQLite engine (single shared connection); nothing touches disk."""
    test_engine = create_async_engine(
        "sqlite+aiosqlite://",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    await init_db(test_engine)
    yield test_engine
    await test_engine.dispose()


@pytest.fixture
def session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Session factory bound to the in-memory engine."""
    return async_sessionmaker(engine, expire_on_commit=False)


@pytest.fixture
async def session(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[AsyncSession]:
    """One session on the in-memory database."""
    async with session_factory() as db_session:
        yield db_session


@pytest.fixture
async def client(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[httpx.AsyncClient]:
    """API client with the in-memory database."""

    async def _session() -> AsyncIterator[AsyncSession]:
        async with session_factory() as db_session:
            yield db_session

    app.dependency_overrides[get_session] = _session
    app.dependency_overrides[get_detector] = lambda: ScamDetector()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as api_client:
        yield api_client
    app.dependency_overrides.clear()
