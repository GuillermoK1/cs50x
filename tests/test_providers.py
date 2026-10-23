import pytest

from job_filter.adapters.base import JobProvider
from job_filter.core.schemas import JobSummary


def test_job_provider_cannot_be_instantiated_directly() -> None:
    """The abstract provider cannot be created without a concrete subclass."""
    with pytest.raises(TypeError):
        JobProvider()  # type: ignore[abstract]


@pytest.mark.asyncio
async def test_minimal_job_provider_subclass_can_be_instantiated_and_fetch_jobs() -> None:
    class MinimalJobProvider(JobProvider):
        @property
        def name(self) -> str:
            return "minimal"

        async def fetch_jobs(self, query: str) -> list[JobSummary]:
            return []

    provider = MinimalJobProvider()

    assert provider.name == "minimal"
    assert isinstance(await provider.fetch_jobs("python"), list)