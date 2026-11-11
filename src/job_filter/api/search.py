"""Search flow shared by the JSON API and the HTML UI."""

from job_filter.adapters.base import JobProvider, ProviderError
from job_filter.api.schemas import JobResult
from job_filter.core.repository import JobRepository
from job_filter.core.scam_detector import ScamDetector


def provider_error_message(provider: JobProvider, exc: ProviderError) -> str:
    """Curated, user-safe message for a provider failure."""
    return f"Job provider '{provider.name}' failed: {exc}"


async def run_search(
    provider: JobProvider,
    detector: ScamDetector,
    repository: JobRepository,
    *,
    query: str,
    location: str | None,
    page: int,
    limit: int,
    exclude_scams: bool,
) -> list[JobResult]:
    """Fetch jobs, score and store all of them, then return them (optionally without scams).

    ``ProviderError`` propagates to the caller.
    """
    # 1. Fetch normalized jobs from the provider.
    jobs = await provider.fetch_jobs(query, location=location, page=page, limit=limit)
    # 2. Score every job; reports keep the same order as jobs.
    reports = detector.analyze_many(jobs)
    # 3. Persist all jobs (even suspicious ones) before any filtering.
    await repository.save_results(jobs, reports)

    # 4. Merge each job with its report; zip is strict because both lists must match.
    # exclude_scams only hides suspicious jobs from the response, not from the database.
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
