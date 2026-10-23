"""Initial tests for the shared job model and future filtering behavior."""

import pytest
from pydantic import ValidationError

from job_filter.core.schemas import JobSummary


def test_valid_job_has_normalized_fields(valid_job: JobSummary) -> None:
    """A valid job offer can be represented by the shared model."""
    assert valid_job.title == "Python Developer"
    assert str(valid_job.url) == "https://example.com/jobs/example-1"


@pytest.mark.asyncio
async def test_job_summary_can_be_used_in_async_tests(valid_job: JobSummary) -> None:
    """The model is available to asynchronous tests."""
    assert valid_job.salary_min is not None
    assert valid_job.salary_max is not None
    assert valid_job.salary_min <= valid_job.salary_max


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("title", " "),
        ("salary_min", -1),
        ("salary_max", -1),
        ("salary_min", 90_000),
        ("url", "not-a-url"),
    ],
)
def test_job_summary_rejects_invalid_fields(
    valid_job: JobSummary,
    field: str,
    value: str | int,
) -> None:
    """Invalid titles, salaries, and URLs are rejected."""
    job_data = valid_job.model_dump()
    job_data[field] = value

    with pytest.raises(ValidationError):
        JobSummary(**job_data)


# TODO (Phase 2/3): add ScamDetector unit tests when the detector is implemented.
