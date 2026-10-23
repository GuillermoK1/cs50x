"""Shared data models for normalized job offers."""

from datetime import datetime

from pydantic import BaseModel, HttpUrl, field_validator, model_validator


class JobSummary(BaseModel):
    """Provider-independent representation of a job offer.

    In Phase 2, each adapter will translate its provider's native response
    format into this model.
    """

    id: str
    title: str
    company: str
    description: str | None = None
    location: str | None = None
    salary_min: float | None = None
    salary_max: float | None = None
    currency: str | None = None
    url: HttpUrl
    posted_at: datetime | None = None
    source: str

    @field_validator("title")
    @classmethod
    def title_must_not_be_empty(cls, value: str) -> str:
        """Reject titles that are empty or contain only whitespace."""
        if not value.strip():
            raise ValueError("title must not be empty")
        return value

    @field_validator("salary_min", "salary_max")
    @classmethod
    def salary_must_not_be_negative(cls, value: float | None) -> float | None:
        """Reject negative salary amounts when provided."""
        if value is not None and value < 0:
            raise ValueError("salary amounts must not be negative")
        return value

    @model_validator(mode="after")
    def minimum_salary_must_not_exceed_maximum(self) -> "JobSummary":
        """Ensure a supplied salary range is ordered correctly."""
        if (
            self.salary_min is not None
            and self.salary_max is not None
            and self.salary_min > self.salary_max
        ):
            raise ValueError("salary_min must not exceed salary_max")
        return self
