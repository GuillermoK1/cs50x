"""Adzuna adapter: native models plus translation to ``JobSummary``."""

from datetime import datetime
from typing import Any

import httpx
from pydantic import BaseModel, ValidationError, field_validator

from job_filter.adapters.base import JobProvider
from job_filter.core.config import settings
from job_filter.core.schemas import JobSummary

BASE_URL = "https://api.adzuna.com/v1/api/jobs"


class ProviderError(Exception):
    """Raised when a provider fails (network, HTTP status, bad payload, config)."""


class AdzunaNamed(BaseModel):
    """Adzuna nested object (company/location) with a display name."""

    display_name: str | None = None


class AdzunaJob(BaseModel):
    """One listing in Adzuna's native format (only the fields we use)."""

    id: str | int | None = None
    title: str | None = None
    description: str | None = None
    created: datetime | None = None
    redirect_url: str | None = None
    salary_min: float | None = None
    salary_max: float | None = None
    salary_is_predicted: bool = False
    company: AdzunaNamed | None = None
    location: AdzunaNamed | None = None

    @field_validator("salary_is_predicted", mode="before")
    @classmethod
    def _parse_predicted(cls, value: Any) -> bool:
        """Accept bool, 0/1 or "0"/"1" (Adzuna's docs do not state the type)."""
        if value is None:
            return False
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true"}
        return bool(value)


class AdzunaResponse(BaseModel):
    """Adzuna search response."""

    count: int | None = None
    results: list[AdzunaJob]


class AdzunaProvider(JobProvider):
    """Fetch jobs from the Adzuna API.

    Country and credentials come from Settings unless passed explicitly.
    An injected ``client`` is never closed; otherwise one is created per call.
    """

    def __init__(
        self,
        *,
        app_id: str | None = None,
        app_key: str | None = None,
        country: str | None = None,
        max_days_old: int | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._app_id = app_id or settings.adzuna_app_id
        self._app_key = app_key or (
            settings.adzuna_app_key.get_secret_value() if settings.adzuna_app_key else None
        )
        self._country = country or settings.adzuna_country
        self._max_days_old = max_days_old
        self._client = client

    @property
    def name(self) -> str:
        return "adzuna"

    async def fetch_jobs(
        self,
        query: str,
        *,
        location: str | None = None,
        page: int = 1,
        limit: int = 20,
    ) -> list[JobSummary]:
        """Search Adzuna and return normalized jobs; raise ProviderError on failure."""
        if not self._app_id or not self._app_key:
            raise ProviderError("Adzuna credentials are missing (ADZUNA_APP_ID/ADZUNA_APP_KEY).")
        params: dict[str, str | int] = {
            "app_id": self._app_id,
            "app_key": self._app_key,
            "what": query,
            "results_per_page": limit,
        }
        if location:
            params["where"] = location
        if self._max_days_old is not None:
            params["max_days_old"] = self._max_days_old
        url = f"{BASE_URL}/{self._country}/search/{page}"

        try:
            if self._client is not None:
                response = await self._client.get(url, params=params)
            else:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.get(url, params=params)
        except httpx.HTTPError as exc:
            raise ProviderError(f"Adzuna request failed: {type(exc).__name__}") from exc

        if response.status_code != 200:
            raise ProviderError(f"Adzuna returned HTTP {response.status_code}.")
        try:
            parsed = AdzunaResponse.model_validate(response.json())
        except (ValueError, ValidationError) as exc:
            raise ProviderError("Adzuna returned malformed or unexpected JSON.") from exc

        jobs = (self._translate(item) for item in parsed.results)
        return [job for job in jobs if job is not None]

    @staticmethod
    def _translate(item: AdzunaJob) -> JobSummary | None:
        """Convert a native job to ``JobSummary``.

        Offers missing id, title or redirect_url are skipped (None). Other
        missing fields become None; company falls back to "" (the schema
        allows it and ScamDetector flags empty companies). Predicted salaries
        are kept but flagged; descriptions are always marked truncated.
        """
        if item.id is None or not item.title or not item.redirect_url:
            return None
        try:
            return JobSummary(
                id=str(item.id),
                title=item.title,
                company=(item.company.display_name if item.company else None) or "",
                description=item.description,
                location=item.location.display_name if item.location else None,
                salary_min=item.salary_min,
                salary_max=item.salary_max,
                url=item.redirect_url,
                posted_at=item.created,
                source="adzuna",
                salary_is_predicted=item.salary_is_predicted,
                description_truncated=True,
            )
        except ValidationError:
            return None
