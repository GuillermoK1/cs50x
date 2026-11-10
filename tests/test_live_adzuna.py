"""Live Adzuna check (excluded by default).

Run: python -m pytest -m live -o addopts="" -s
"""

import pytest

from job_filter.adapters.adzuna import AdzunaProvider
from job_filter.core.config import settings
from job_filter.core.schemas import JobSummary

pytestmark = pytest.mark.live


async def test_real_adzuna_translates_to_job_summary() -> None:
    if not settings.adzuna_app_id or not settings.adzuna_app_key:
        pytest.skip("Adzuna credentials not configured in .env")
    jobs = await AdzunaProvider(max_days_old=30).fetch_jobs("python", limit=5)
    assert isinstance(jobs, list)
    assert all(isinstance(job, JobSummary) and job.source == "adzuna" for job in jobs)
    assert all(isinstance(job.salary_is_predicted, bool) for job in jobs)
    predicted = sum(job.salary_is_predicted for job in jobs)
    print(f"live: {len(jobs)} job(s) translated; predicted salaries: {predicted}")
