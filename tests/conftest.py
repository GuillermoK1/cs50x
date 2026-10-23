"""Shared pytest fixtures."""

import pytest

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
