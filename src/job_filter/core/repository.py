"""Persistence of scored jobs; maps between ORM rows and domain models."""

from datetime import timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from job_filter.core.models import JobRow
from job_filter.core.scam_detector import Flag, ScamReport
from job_filter.core.schemas import JobSummary


def _to_row(job: JobSummary, report: ScamReport) -> JobRow:
    posted_at = job.posted_at
    if posted_at is not None and posted_at.tzinfo is not None:
        posted_at = posted_at.astimezone(timezone.utc).replace(tzinfo=None)
    return JobRow(
        source=job.source,
        id=job.id,
        title=job.title,
        company=job.company,
        description=job.description,
        location=job.location,
        salary_min=job.salary_min,
        salary_max=job.salary_max,
        currency=job.currency,
        url=str(job.url),
        posted_at=posted_at,
        salary_is_predicted=job.salary_is_predicted,
        description_truncated=job.description_truncated,
        scam_score=report.score,
        is_suspicious=report.is_suspicious,
        flags=[flag.model_dump() for flag in report.flags],
    )


def _from_row(row: JobRow) -> tuple[JobSummary, ScamReport]:
    # SQLite drops tzinfo, so stored values are re-read as UTC.
    posted_at = row.posted_at.replace(tzinfo=timezone.utc) if row.posted_at else None
    job = JobSummary(
        id=row.id,
        title=row.title,
        company=row.company,
        description=row.description,
        location=row.location,
        salary_min=row.salary_min,
        salary_max=row.salary_max,
        currency=row.currency,
        url=row.url,
        posted_at=posted_at,
        source=row.source,
        salary_is_predicted=row.salary_is_predicted,
        description_truncated=row.description_truncated,
    )
    report = ScamReport(
        job_id=row.id,
        score=row.scam_score,
        flags=[Flag(**flag) for flag in row.flags],
        is_suspicious=row.is_suspicious,
    )
    return job, report


class JobRepository:
    """Async access to the ``jobs`` table."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save_results(self, jobs: list[JobSummary], reports: list[ScamReport]) -> None:
        """Upsert each job with its report (by source + id) and commit."""
        for job, report in zip(jobs, reports, strict=True):
            # merge = upsert by primary key (source, id), so repeated searches don't duplicate rows.
            await self._session.merge(_to_row(job, report))
        # One commit for the whole batch.
        await self._session.commit()

    async def list_jobs(
        self,
        source: str | None = None,
        exclude_scams: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> list[tuple[JobSummary, ScamReport]]:
        """Return stored jobs with their reports, optionally filtered."""
        statement = select(JobRow).order_by(JobRow.source, JobRow.id)
        if source is not None:
            statement = statement.where(JobRow.source == source)
        if exclude_scams:
            statement = statement.where(JobRow.is_suspicious.is_(False))
        result = await self._session.scalars(statement.limit(limit).offset(offset))
        return [_from_row(row) for row in result]
