"""API response models."""

from job_filter.core.scam_detector import Flag
from job_filter.core.schemas import JobSummary


class JobResult(JobSummary):
    """A job plus its scam analysis."""

    scam_score: int
    is_suspicious: bool
    flags: list[Flag]
