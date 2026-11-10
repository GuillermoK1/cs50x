"""Abstract contract for job-provider adapters."""

from abc import ABC, abstractmethod

from job_filter.core.schemas import JobSummary


class ProviderError(Exception):
    """Raised when a provider fails (network, HTTP status, bad payload, config)."""


class JobProvider(ABC):
    """Define the interface that each job-provider adapter must implement.

    Concrete adapters are responsible for translating a provider's native
    response format into the shared :class:`JobSummary` model.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the identifier used for this provider's jobs."""

    @abstractmethod
    async def fetch_jobs(
        self,
        query: str,
        *,
        location: str | None = None,
        page: int = 1,
        limit: int = 20,
    ) -> list[JobSummary]:
        """Fetch jobs matching ``query`` and normalize them to ``JobSummary``.

        ``location`` optionally narrows results, ``page`` starts at 1 and
        ``limit`` caps the jobs returned per page. Provider-specific settings
        (country, credentials) belong in the adapter constructor.

        Implementations should perform asynchronous I/O and return an empty
        list when the provider has no matching jobs.
        """
