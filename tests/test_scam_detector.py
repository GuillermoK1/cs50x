"""Tests for ScamDetector rules, scoring and filtering."""

from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from typing import Any

import pytest

from job_filter.adapters.mock import MockProvider
from job_filter.core.scam_detector import DEFAULT_WEIGHTS, ScamDetector
from job_filter.core.schemas import JobSummary

NOW = datetime(2025, 3, 1, tzinfo=timezone.utc)
GOOD_DESC = "We build and maintain backend services and you will join a small team."

MakeJob = Callable[..., JobSummary]


@pytest.fixture
def detector() -> ScamDetector:
    return ScamDetector(now=lambda: NOW)


@pytest.mark.parametrize(
    ("overrides", "code", "expected"),
    [
        ({"salary_min": 500_000, "salary_max": 900_000}, "unrealistic_salary", True),
        ({"salary_min": 1_000, "salary_max": 50_000}, "unrealistic_salary", True),
        (
            {"salary_min": 500_000, "salary_max": 900_000, "salary_is_predicted": True},
            "unrealistic_salary",
            False,
        ),
        ({"salary_min": 40_000, "salary_max": 60_000}, "unrealistic_salary", False),
        ({"description": GOOD_DESC + " No experience needed."}, "scam_keywords", True),
        ({"description": GOOD_DESC + " Inversión inicial requerida."}, "scam_keywords", True),
        ({"description": GOOD_DESC}, "scam_keywords", False),
        ({"description": GOOD_DESC + " Write on WhatsApp."}, "off_platform_contact", True),
        ({"description": GOOD_DESC + " Mail jobs@gmail.com"}, "off_platform_contact", True),
        ({"description": GOOD_DESC + " Mail jobs@acme.com"}, "off_platform_contact", False),
        ({"company": "Confidential"}, "missing_company", True),
        ({"company": "  "}, "missing_company", True),
        ({"company": "Acme"}, "missing_company", False),
        ({"description": "Apply."}, "short_description", True),
        ({"description": None}, "short_description", True),
        ({"description": "Apply.", "description_truncated": True}, "short_description", False),
        ({"description": GOOD_DESC}, "short_description", False),
        ({"posted_at": NOW - timedelta(days=61)}, "old_listing", True),
        ({"posted_at": NOW - timedelta(days=5)}, "old_listing", False),
        ({"posted_at": None}, "old_listing", False),
        ({"posted_at": datetime(2024, 1, 1)}, "old_listing", True),
    ],
    ids=[
        "salary-too-high",
        "salary-ratio",
        "salary-predicted-ignored",
        "salary-ok",
        "keyword-en",
        "keyword-es",
        "keyword-none",
        "whatsapp",
        "free-email",
        "corporate-email",
        "company-generic",
        "company-empty",
        "company-ok",
        "desc-short",
        "desc-none",
        "desc-truncated-ignored",
        "desc-ok",
        "old-listing",
        "recent-listing",
        "no-date",
        "naive-datetime",
    ],
)
def test_rule_triggers(
    detector: ScamDetector,
    make_job: MakeJob,
    overrides: dict[str, Any],
    code: str,
    expected: bool,
) -> None:
    base = {"description": GOOD_DESC, "posted_at": NOW - timedelta(days=1)}
    job = make_job(**(base | overrides))
    triggered = {flag.code for flag in detector.analyze(job).flags}
    assert (code in triggered) is expected


def test_clean_job_scores_zero(detector: ScamDetector, make_job: MakeJob) -> None:
    report = detector.analyze(make_job(description=GOOD_DESC, posted_at=NOW))
    assert report.score == 0
    assert report.flags == []
    assert not report.is_suspicious


def test_flags_have_readable_reasons(detector: ScamDetector, make_job: MakeJob) -> None:
    report = detector.analyze(make_job(company="Confidential", description="Hi"))
    assert report.flags
    assert all(flag.reason for flag in report.flags)


def test_score_is_sum_of_weights(detector: ScamDetector, make_job: MakeJob) -> None:
    job = make_job(
        description=GOOD_DESC + " WhatsApp me", company="Confidential", posted_at=NOW
    )
    expected = DEFAULT_WEIGHTS["off_platform_contact"] + DEFAULT_WEIGHTS["missing_company"]
    assert detector.analyze(job).score == expected


def test_score_is_capped_at_100(detector: ScamDetector, make_job: MakeJob) -> None:
    job = make_job(
        description="Pay upfront payment, WhatsApp",
        company="Confidential",
        salary_min=500_000,
        salary_max=900_000,
        posted_at=NOW - timedelta(days=400),
    )
    report = detector.analyze(job)
    assert sum(DEFAULT_WEIGHTS.values()) > 100
    assert report.score == 100
    assert report.is_suspicious


@pytest.mark.parametrize(
    ("threshold", "suspicious"),
    [(45, True), (46, False)],
    ids=["at-threshold", "above-score"],
)
def test_threshold_is_configurable(
    make_job: MakeJob, threshold: int, suspicious: bool
) -> None:
    detector = ScamDetector(threshold=threshold, now=lambda: NOW)
    job = make_job(description=GOOD_DESC + " WhatsApp", company="Confidential", posted_at=NOW)
    report = detector.analyze(job)
    assert report.score == 45
    assert report.is_suspicious is suspicious


def test_weight_override(make_job: MakeJob) -> None:
    detector = ScamDetector(weights={"missing_company": 80}, now=lambda: NOW)
    job = make_job(company="Confidential", description=GOOD_DESC, posted_at=NOW)
    report = detector.analyze(job)
    assert report.score == 80
    assert report.is_suspicious


def test_injected_now_controls_age(make_job: MakeJob) -> None:
    job = make_job(description=GOOD_DESC, posted_at=NOW)
    later = ScamDetector(now=lambda: NOW + timedelta(days=90)).analyze(job)
    same_day = ScamDetector(now=lambda: NOW).analyze(job)
    assert "old_listing" in {f.code for f in later.flags}
    assert "old_listing" not in {f.code for f in same_day.flags}


def test_filter_removes_suspicious_jobs(detector: ScamDetector, make_job: MakeJob) -> None:
    good = make_job(id="good", description=GOOD_DESC, posted_at=NOW)
    bad = make_job(id="bad", description="upfront payment via WhatsApp", posted_at=NOW)
    assert [job.id for job in detector.filter([good, bad])] == ["good"]


async def test_detector_flags_mock_scams() -> None:
    detector = ScamDetector(now=lambda: datetime(2025, 1, 20, tzinfo=timezone.utc))
    jobs = await MockProvider().fetch_jobs("")
    flagged = {job.id for job in jobs if detector.analyze(job).flags}
    clean = {job.id for job in jobs} - flagged
    assert clean == {"mock-1", "mock-2", "mock-3"}
    assert {f.code for job in jobs for f in detector.analyze(job).flags} == set(DEFAULT_WEIGHTS)
