"""Deterministic in-memory provider used for tests and demos."""

from datetime import datetime, timezone

from job_filter.adapters.base import JobProvider
from job_filter.core.schemas import JobSummary

_RECENT = datetime(2025, 1, 10, tzinfo=timezone.utc)
_OLD = datetime(2023, 1, 10, tzinfo=timezone.utc)

_GOOD_DESCRIPTION = (
    "We are looking for an engineer to design, build and maintain services "
    "for our product. You will work with a small team and review code."
)


def _job(job_id: str, title: str, **overrides: object) -> JobSummary:
    """Build a mock job with sensible defaults."""
    data: dict[str, object] = {
        "id": job_id,
        "title": title,
        "company": "Acme Software",
        "description": _GOOD_DESCRIPTION,
        "location": "Madrid",
        "salary_min": 35_000,
        "salary_max": 50_000,
        "currency": "EUR",
        "url": f"https://mock.example.com/jobs/{job_id}",
        "posted_at": _RECENT,
        "source": "mock",
    }
    return JobSummary(**(data | overrides))


_MOCK_JOBS: list[JobSummary] = [
    _job("mock-1", "Python Developer"),
    _job("mock-2", "Data Analyst", location="Barcelona", company="Datalytics"),
    _job("mock-3", "Backend Engineer", location="Remote", company="Cloudify"),
    _job(
        "mock-4",
        "Python Developer (earn fast)",
        salary_min=500_000,
        salary_max=900_000,
        company="Fast Money Ltd",
    ),
    _job(
        "mock-5",
        "Home Assistant",
        description="No experience needed, guaranteed earnings. Pay a registration fee upfront. Message us on WhatsApp.",
    ),
    _job(
        "mock-6",
        "Remote Data Entry",
        description="Contact us on WhatsApp or at hiring.team@gmail.com to start today.",
        location="Remote",
        salary_max=400_000,
    ),
    _job("mock-7", "Sales Agent", company="Confidential"),
    _job("mock-8", "Python Developer", description="Apply now."),
    _job("mock-9", "Python Developer (legacy)", posted_at=_OLD, location="Valencia"),
]


class MockProvider(JobProvider):
    """Return a fixed list of normal and suspicious jobs without any I/O."""

    @property
    def name(self) -> str:
        return "mock"

    async def fetch_jobs(
        self,
        query: str,
        *,
        location: str | None = None,
        page: int = 1,
        limit: int = 20,
    ) -> list[JobSummary]:
        """Filter by query/location (case-insensitive substring), then paginate."""
        needle = query.strip().lower()
        jobs = [
            job
            for job in _MOCK_JOBS
            if needle in f"{job.title} {job.description or ''}".lower()
            and (location is None or location.lower() in (job.location or "").lower())
        ]
        start = (max(page, 1) - 1) * limit
        return [job.model_copy() for job in jobs[start : start + limit]]
