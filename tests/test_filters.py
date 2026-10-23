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
    ("overrides", "expected_field"),
    [
        ({"title": " "}, "title"),
        ({"salary_min": -1, "salary_max": None}, "salary_min"),
        ({"salary_min": None, "salary_max": -1}, "salary_max"),
        ({"salary_min": 90_000, "salary_max": 50_000}, None),
        ({"url": "not-a-url"}, "url"),
    ],
    ids=["blank-title", "negative-min", "negative-max", "min-greater-than-max", "bad-url"],
)
def test_job_summary_rejects_invalid_fields(
    valid_job: JobSummary,
    overrides: dict,
    expected_field: str | None,
) -> None:
    """Invalid titles, salaries, and URLs are rejected."""
    job_data = valid_job.model_dump() | overrides

    with pytest.raises(ValidationError) as exc_info:
        JobSummary(**job_data)

    if expected_field is not None:
        assert any(expected_field in err["loc"] for err in exc_info.value.errors())


@pytest.mark.parametrize(
    "overrides",
    [
        {"salary_min": None, "salary_max": None},
        {"salary_min": 50_000, "salary_max": None},
        {"salary_min": None, "salary_max": 50_000},
        {"salary_min": 50_000, "salary_max": 50_000},
        {"salary_min": 0, "salary_max": 0},
    ],
    ids=["no-salary", "only-min", "only-max", "equal", "zero"],
)
def test_job_summary_accepts_valid_salary_edge_cases(
    valid_job: JobSummary,
    overrides: dict,
) -> None:
    """Valid salary combinations, including missing and boundary values, are accepted."""
    JobSummary(**(valid_job.model_dump() | overrides))


# TODO (Phase 2/3): add ScamDetector unit tests when the detector is implemented.