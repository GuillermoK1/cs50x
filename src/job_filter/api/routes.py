"""HTTP routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from job_filter.adapters.base import JobProvider, ProviderError
from job_filter.api.dependencies import get_detector, get_provider, get_repository
from job_filter.api.schemas import JobResult
from job_filter.api.search import provider_error_message, run_search
from job_filter.core.repository import JobRepository
from job_filter.core.scam_detector import ScamDetector

router = APIRouter()


@router.get("/jobs/search", response_model=list[JobResult])
async def search_jobs(
    provider: Annotated[JobProvider, Depends(get_provider)],
    detector: Annotated[ScamDetector, Depends(get_detector)],
    repository: Annotated[JobRepository, Depends(get_repository)],
    query: Annotated[str, Query(min_length=1)],
    location: str | None = None,
    page: Annotated[int, Query(ge=1, le=100)] = 1,
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
    exclude_scams: bool = False,
) -> list[JobResult]:
    """Fetch jobs, score and store all of them, then return them (optionally without scams)."""
    # Providers, detector and repository are injected so tests can override them.
    try:
        return await run_search(
            provider,
            detector,
            repository,
            query=query,
            location=location,
            page=page,
            limit=limit,
            exclude_scams=exclude_scams,
        )
    except ProviderError as exc:
        # Upstream provider failure -> 502 Bad Gateway (not our own error).
        raise HTTPException(status_code=502, detail=provider_error_message(provider, exc)) from exc
