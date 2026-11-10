"""HTTP routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from job_filter.adapters.base import JobProvider, ProviderError
from job_filter.api.dependencies import get_detector, get_provider, get_repository
from job_filter.api.schemas import JobResult
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
    try:
        jobs = await provider.fetch_jobs(query, location=location, page=page, limit=limit)
    except ProviderError as exc:
        raise HTTPException(
            status_code=502, detail=f"Job provider '{provider.name}' failed: {exc}"
        ) from exc

    reports = detector.analyze_many(jobs)
    await repository.save_results(jobs, reports)

    return [
        JobResult(
            **job.model_dump(),
            scam_score=report.score,
            is_suspicious=report.is_suspicious,
            flags=report.flags,
        )
        for job, report in zip(jobs, reports, strict=True)
        if not (exclude_scams and report.is_suspicious)
    ]
