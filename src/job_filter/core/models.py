"""ORM models (kept separate from the ``JobSummary`` domain model)."""

from datetime import datetime
from typing import Any

from sqlalchemy import JSON
from sqlalchemy.orm import Mapped, mapped_column

from job_filter.core.database import Base


class JobRow(Base):
    """A scored job offer, keyed by (source, id)."""

    __tablename__ = "jobs"

    source: Mapped[str] = mapped_column(primary_key=True)
    id: Mapped[str] = mapped_column(primary_key=True)
    title: Mapped[str]
    company: Mapped[str]
    description: Mapped[str | None]
    location: Mapped[str | None]
    salary_min: Mapped[float | None]
    salary_max: Mapped[float | None]
    currency: Mapped[str | None]
    url: Mapped[str]
    posted_at: Mapped[datetime | None]  # naive UTC
    salary_is_predicted: Mapped[bool]
    description_truncated: Mapped[bool]
    scam_score: Mapped[int]
    is_suspicious: Mapped[bool]
    flags: Mapped[list[dict[str, Any]]] = mapped_column(JSON)
