"""FastAPI dependencies (overridable in tests)."""

from typing import Annotated, Literal

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from job_filter.adapters.adzuna import AdzunaProvider
from job_filter.adapters.base import JobProvider
from job_filter.adapters.mock import MockProvider
from job_filter.core.database import get_session
from job_filter.core.repository import JobRepository
from job_filter.core.scam_detector import ScamDetector


def get_provider(source: Literal["mock", "adzuna"] = "mock") -> JobProvider:
    """Build the provider for ``source``; Adzuna only when requested."""
    if source == "adzuna":
        return AdzunaProvider()
    return MockProvider()


def get_detector() -> ScamDetector:
    """Return the default detector."""
    return ScamDetector()


def get_repository(session: Annotated[AsyncSession, Depends(get_session)]) -> JobRepository:
    """Build a repository bound to the request session."""
    return JobRepository(session)
