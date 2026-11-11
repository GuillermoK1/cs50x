"""FastAPI dependencies (overridable in tests)."""

from collections.abc import Callable
from typing import Annotated, Literal, TypeGuard, get_args

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from job_filter.adapters.adzuna import AdzunaProvider
from job_filter.adapters.base import JobProvider
from job_filter.adapters.mock import MockProvider
from job_filter.core.database import get_session
from job_filter.core.repository import JobRepository
from job_filter.core.scam_detector import ScamDetector


Source = Literal["mock", "adzuna"]
SOURCES: tuple[Source, ...] = get_args(Source)


def is_source(value: str) -> TypeGuard[Source]:
    """True when ``value`` is a supported source name."""
    return value in SOURCES


def get_provider(source: Source = "mock") -> JobProvider:
    """Build the provider for ``source``; Adzuna only when requested."""
    # Adzuna is built lazily so the mock path never needs API credentials.
    if source == "adzuna":
        return AdzunaProvider()
    return MockProvider()


def get_provider_factory() -> Callable[[Source], JobProvider]:
    """Return the provider builder, for routes that validate ``source`` themselves."""
    # Lets the HTML route return a 400 for a bad source instead of FastAPI's 422.
    return get_provider


def get_detector() -> ScamDetector:
    """Return the default detector."""
    return ScamDetector()


def get_repository(session: Annotated[AsyncSession, Depends(get_session)]) -> JobRepository:
    """Build a repository bound to the request session."""
    return JobRepository(session)
