"""Rule-based scam and ghost-job detector.

These are simple heuristics: they WILL produce false positives (legitimate
jobs flagged) and false negatives (scams that pass). Treat scores as hints.
"""

from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from typing import Protocol

from pydantic import BaseModel, Field

from job_filter.core.schemas import JobSummary

SCAM_KEYWORDS: tuple[str, ...] = (
    # English
    "upfront payment",
    "registration fee",
    "initial investment",
    "no experience needed",
    "guaranteed earnings",
    "guaranteed income",
    "wire transfer",
    "western union",
    "cryptocurrency",
    "bitcoin",
    # Spanish
    "pago por adelantado",
    "pago inicial",
    "inversión inicial",
    "inversion inicial",
    "sin experiencia",
    "ganancias garantizadas",
    "ingresos garantizados",
    "transferencia bancaria",
    "criptomonedas",
)

OFF_PLATFORM_KEYWORDS: tuple[str, ...] = ("whatsapp", "telegram")
FREE_EMAIL_DOMAINS: tuple[str, ...] = (
    "gmail.com",
    "hotmail.com",
    "outlook.com",
    "yahoo.com",
    "yahoo.es",
    "protonmail.com",
)
GENERIC_COMPANY_NAMES: frozenset[str] = frozenset(
    {
        "confidential",
        "confidencial",
        "anonymous",
        "anónimo",
        "anonimo",
        "n/a",
        "unknown",
        "desconocido",
        "company",
        "empresa",
        "private",
        "hiring",
    }
)

MAX_REALISTIC_SALARY = 300_000
MAX_SALARY_RATIO = 10
MIN_DESCRIPTION_LENGTH = 40
OLD_LISTING_DAYS = 60

DEFAULT_WEIGHTS: dict[str, int] = {
    "unrealistic_salary": 30,
    "scam_keywords": 40,
    "off_platform_contact": 30,
    "missing_company": 15,
    "short_description": 15,
    "old_listing": 20,
}


class Flag(BaseModel):
    """A triggered rule with a human-readable reason."""

    code: str
    reason: str


class ScamReport(BaseModel):
    """Result of analyzing one job."""

    job_id: str
    score: int = Field(ge=0, le=100)
    flags: list[Flag]
    is_suspicious: bool


class Rule(Protocol):
    """A rule returns a reason when triggered, otherwise None."""

    code: str

    def check(self, job: JobSummary, now: datetime) -> str | None: ...


def _text(job: JobSummary) -> str:
    return f"{job.title} {job.description or ''}".lower()


class UnrealisticSalaryRule:
    """Very high salary or a disproportionate min/max range."""

    code = "unrealistic_salary"

    def check(self, job: JobSummary, now: datetime) -> str | None:
        if job.salary_is_predicted:
            return None
        top = job.salary_max if job.salary_max is not None else job.salary_min
        if top is not None and top > MAX_REALISTIC_SALARY:
            return f"Salary {top:,.0f} exceeds {MAX_REALISTIC_SALARY:,}."
        if (
            job.salary_min
            and job.salary_max is not None
            and job.salary_max / job.salary_min > MAX_SALARY_RATIO
        ):
            return f"Salary range is disproportionate (more than {MAX_SALARY_RATIO}x)."
        return None


class ScamKeywordsRule:
    """Typical scam phrases in English and Spanish."""

    code = "scam_keywords"

    def check(self, job: JobSummary, now: datetime) -> str | None:
        text = _text(job)
        found = [word for word in SCAM_KEYWORDS if word in text]
        return f"Contains scam phrases: {', '.join(found)}." if found else None


class OffPlatformContactRule:
    """Asks to be contacted through messaging apps or free email."""

    code = "off_platform_contact"

    def check(self, job: JobSummary, now: datetime) -> str | None:
        text = _text(job)
        found = [word for word in OFF_PLATFORM_KEYWORDS if word in text]
        found += [d for d in FREE_EMAIL_DOMAINS if f"@{d}" in text]
        return f"Asks for off-platform contact: {', '.join(found)}." if found else None


class MissingCompanyRule:
    """Empty or generic company name."""

    code = "missing_company"

    def check(self, job: JobSummary, now: datetime) -> str | None:
        name = job.company.strip().lower()
        if not name:
            return "Company name is empty."
        if name in GENERIC_COMPANY_NAMES:
            return f"Company name '{job.company}' is generic."
        return None


class ShortDescriptionRule:
    """Empty or very short description (ignored when truncated by provider)."""

    code = "short_description"

    def check(self, job: JobSummary, now: datetime) -> str | None:
        if job.description_truncated:
            return None
        length = len((job.description or "").strip())
        if length < MIN_DESCRIPTION_LENGTH:
            return f"Description is empty or too short ({length} characters)."
        return None


class OldListingRule:
    """Listing posted long ago (possible ghost job). Naive datetimes are read as UTC."""

    code = "old_listing"

    def check(self, job: JobSummary, now: datetime) -> str | None:
        if job.posted_at is None:
            return None
        posted = job.posted_at
        if posted.tzinfo is None:
            posted = posted.replace(tzinfo=timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)
        age = now - posted
        if age > timedelta(days=OLD_LISTING_DAYS):
            return f"Listing is {age.days} days old (limit {OLD_LISTING_DAYS})."
        return None


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ScamDetector:
    """Score jobs with weighted heuristic rules.

    Heuristics only: expect false positives and false negatives.
    ``now`` is an injected clock so date rules are deterministic in tests.
    """

    def __init__(
        self,
        threshold: int = 50,
        weights: dict[str, int] | None = None,
        now: Callable[[], datetime] = _utc_now,
    ) -> None:
        self.threshold = threshold
        self.weights = DEFAULT_WEIGHTS | (weights or {})
        self._now = now
        self.rules: list[Rule] = [
            UnrealisticSalaryRule(),
            ScamKeywordsRule(),
            OffPlatformContactRule(),
            MissingCompanyRule(),
            ShortDescriptionRule(),
            OldListingRule(),
        ]

    def analyze(self, job: JobSummary) -> ScamReport:
        """Run all rules and build a report."""
        now = self._now()
        flags: list[Flag] = []
        score = 0
        for rule in self.rules:
            reason = rule.check(job, now)
            if reason is not None:
                flags.append(Flag(code=rule.code, reason=reason))
                score += self.weights.get(rule.code, 0)
        score = min(score, 100)
        return ScamReport(
            job_id=job.id,
            score=score,
            flags=flags,
            is_suspicious=score >= self.threshold,
        )

    def analyze_many(self, jobs: list[JobSummary]) -> list[ScamReport]:
        """Analyze each job and return the reports in the same order."""
        return [self.analyze(job) for job in jobs]

    def filter(self, jobs: list[JobSummary]) -> list[JobSummary]:
        """Return only the jobs that are not suspicious."""
        return [job for job in jobs if not self.analyze(job).is_suspicious]
