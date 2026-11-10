"""Tests for MockProvider."""

from collections.abc import Callable
from datetime import datetime, timezone

import pytest

from job_filter.adapters.base import JobProvider
from job_filter.adapters.mock import MockProvider
from job_filter.core.scam_detector import ScamDetector
from job_filter.core.schemas import JobSummary


async def test_mock_fulfills_provider_contract() -> None:
    provider = MockProvider()
    assert isinstance(provider, JobProvider)
    assert provider.name == "mock"


async def test_mock_returns_valid_job_summaries() -> None:
    jobs = await MockProvider().fetch_jobs("")
    assert jobs
    assert all(isinstance(job, JobSummary) and job.source == "mock" for job in jobs)
    assert len({job.id for job in jobs}) == len(jobs)


async def test_mock_is_deterministic() -> None:
    provider = MockProvider()
    assert await provider.fetch_jobs("") == await provider.fetch_jobs("")


@pytest.mark.parametrize(
    ("kwargs", "check"),
    [
        ({"query": "data analyst"}, lambda jobs: [j.title for j in jobs] == ["Data Analyst"]),
        ({"query": "", "location": "barcelona"}, lambda jobs: len(jobs) == 1),
        ({"query": "", "limit": 3}, lambda jobs: len(jobs) == 3),
        ({"query": "", "page": 99}, lambda jobs: jobs == []),
        ({"query": "no-such-job"}, lambda jobs: jobs == []),
    ],
    ids=["query", "location", "limit", "page-beyond-end", "no-match"],
)
async def test_mock_filters_and_paginates(
    kwargs: dict[str, object], check: Callable[[list[JobSummary]], bool]
) -> None:
    assert check(await MockProvider().fetch_jobs(**kwargs))  # type: ignore[arg-type]


async def test_mock_pages_do_not_overlap() -> None:
    provider = MockProvider()
    first = await provider.fetch_jobs("", page=1, limit=4)
    second = await provider.fetch_jobs("", page=2, limit=4)
    assert not {j.id for j in first} & {j.id for j in second}


async def test_detector_filters_mock_scams_and_keeps_clean_jobs() -> None:
    detector = ScamDetector(now=lambda: datetime(2025, 1, 15, tzinfo=timezone.utc))
    jobs = await MockProvider().fetch_jobs("")
    kept = {job.id for job in detector.filter(jobs)}
    assert {"mock-1", "mock-2", "mock-3"} <= kept
    assert not kept & {"mock-5", "mock-6"}
    for job in jobs:
        if job.id in {"mock-5", "mock-6"}:
            report = detector.analyze(job)
            assert len(report.flags) >= 2 and report.is_suspicious
