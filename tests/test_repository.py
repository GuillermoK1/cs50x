"""Repository tests against an in-memory SQLite database."""

from collections.abc import Callable
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from job_filter.core import database
from job_filter.core.models import JobRow
from job_filter.core.repository import JobRepository
from job_filter.core.scam_detector import ScamDetector, ScamReport
from job_filter.core.schemas import JobSummary

NOW = datetime(2025, 1, 15, tzinfo=timezone.utc)
SCAMMY = "No experience needed, guaranteed earnings. Message us on WhatsApp."


@pytest.fixture
def detector() -> ScamDetector:
    return ScamDetector(now=lambda: NOW)


def _analyze(detector: ScamDetector, jobs: list[JobSummary]) -> list[ScamReport]:
    return [detector.analyze(job) for job in jobs]


async def _count(session: AsyncSession) -> int:
    return await session.scalar(select(func.count()).select_from(JobRow)) or 0


async def test_save_twice_does_not_duplicate(
    session: AsyncSession, make_job: Callable[..., JobSummary], detector: ScamDetector
) -> None:
    jobs = [make_job(id="a"), make_job(id="b")]
    repo = JobRepository(session)
    for _ in range(2):
        await repo.save_results(jobs, _analyze(detector, jobs))
    assert await _count(session) == 2


async def test_upsert_updates_existing_row(
    session: AsyncSession, make_job: Callable[..., JobSummary], detector: ScamDetector
) -> None:
    repo = JobRepository(session)
    first = make_job(id="a", title="Old title")
    await repo.save_results([first], _analyze(detector, [first]))
    second = make_job(id="a", title="New title")
    await repo.save_results([second], _analyze(detector, [second]))
    [(stored, _)] = await repo.list_jobs()
    assert stored.title == "New title"


async def test_score_and_flags_round_trip(
    session: AsyncSession, make_job: Callable[..., JobSummary], detector: ScamDetector
) -> None:
    job = make_job(id="scam", description=SCAMMY)
    report = detector.analyze(job)
    repo = JobRepository(session)
    await repo.save_results([job], [report])
    session.expunge_all()
    [(stored_job, stored_report)] = await repo.list_jobs()
    assert stored_report == report
    assert stored_report.is_suspicious
    assert stored_job == job


@pytest.mark.parametrize(
    "posted_at",
    [
        pytest.param(datetime(2025, 1, 10, 8, 30, tzinfo=timezone.utc), id="utc"),
        pytest.param(
            datetime(2025, 1, 10, 10, 30, tzinfo=timezone(timedelta(hours=2))), id="offset"
        ),
        pytest.param(None, id="none"),
    ],
)
async def test_posted_at_keeps_utc(
    session: AsyncSession,
    make_job: Callable[..., JobSummary],
    detector: ScamDetector,
    posted_at: datetime | None,
) -> None:
    job = make_job(id="dated", posted_at=posted_at)
    repo = JobRepository(session)
    await repo.save_results([job], _analyze(detector, [job]))
    session.expunge_all()
    [(stored, _)] = await repo.list_jobs()
    if posted_at is None:
        assert stored.posted_at is None
    else:
        assert stored.posted_at == posted_at
        assert stored.posted_at.utcoffset() == timedelta(0)


async def test_naive_posted_at_is_read_as_utc(
    session: AsyncSession, make_job: Callable[..., JobSummary], detector: ScamDetector
) -> None:
    job = make_job(id="naive", posted_at=datetime(2025, 1, 10, 8, 30))
    repo = JobRepository(session)
    await repo.save_results([job], _analyze(detector, [job]))
    [(stored, _)] = await repo.list_jobs()
    assert stored.posted_at == datetime(2025, 1, 10, 8, 30, tzinfo=timezone.utc)


@pytest.mark.parametrize(
    ("source", "exclude_scams", "expected_ids"),
    [
        pytest.param(None, False, ["ok-1", "ok-2", "scam-1", "x-1"], id="all"),
        pytest.param("example", False, ["ok-1", "ok-2", "scam-1"], id="by-source"),
        pytest.param(None, True, ["ok-1", "ok-2", "x-1"], id="no-scams"),
        pytest.param("example", True, ["ok-1", "ok-2"], id="source-and-no-scams"),
        pytest.param("missing", False, [], id="unknown-source"),
    ],
)
async def test_list_jobs_filters(
    session: AsyncSession,
    make_job: Callable[..., JobSummary],
    detector: ScamDetector,
    source: str | None,
    exclude_scams: bool,
    expected_ids: list[str],
) -> None:
    jobs = [
        make_job(id="ok-1"),
        make_job(id="ok-2"),
        make_job(id="scam-1", description=SCAMMY),
        make_job(id="x-1", source="other"),
    ]
    repo = JobRepository(session)
    await repo.save_results(jobs, _analyze(detector, jobs))
    found = await repo.list_jobs(source=source, exclude_scams=exclude_scams)
    assert [job.id for job, _ in found] == expected_ids


async def test_list_jobs_limit_and_offset(
    session: AsyncSession, make_job: Callable[..., JobSummary], detector: ScamDetector
) -> None:
    jobs = [make_job(id=f"j{i}") for i in range(4)]
    repo = JobRepository(session)
    await repo.save_results(jobs, _analyze(detector, jobs))
    found = await repo.list_jobs(limit=2, offset=1)
    assert [job.id for job, _ in found] == ["j1", "j2"]


async def test_save_results_rejects_length_mismatch(
    session: AsyncSession, make_job: Callable[..., JobSummary], detector: ScamDetector
) -> None:
    jobs = [make_job(id="a"), make_job(id="b")]
    with pytest.raises(ValueError):
        await JobRepository(session).save_results(jobs, _analyze(detector, jobs[:1]))


async def test_init_db_is_idempotent(engine: AsyncEngine) -> None:
    await database.init_db(engine)  # tables already exist: must not fail


async def test_get_session_yields_session(
    monkeypatch: pytest.MonkeyPatch, session_factory: object
) -> None:
    monkeypatch.setattr(database, "async_session_factory", session_factory)
    generator = database.get_session()
    yielded = await anext(generator)
    assert isinstance(yielded, AsyncSession)
    await generator.aclose()
