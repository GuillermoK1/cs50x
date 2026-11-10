"""API tests: mock provider, validation, error mapping (no network, in-memory DB)."""

import httpx
import pytest
import respx
from fastapi import FastAPI
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from job_filter.adapters.adzuna import BASE_URL, AdzunaProvider
from job_filter.adapters.base import JobProvider, ProviderError
from job_filter.adapters.mock import MockProvider
from job_filter.api import main
from job_filter.api.dependencies import get_detector, get_provider
from job_filter.api.main import app
from job_filter.core.models import JobRow
from job_filter.core.scam_detector import ScamDetector
from job_filter.core.schemas import JobSummary

# With the real clock (mock dates are relative to import time), query "e" matches all 9 mock jobs
# and only mock-5 and mock-6 reach the suspicious threshold.
SUSPICIOUS_IDS = {"mock-5", "mock-6"}


class FailingProvider(JobProvider):
    """Provider that always fails with a curated message."""

    @property
    def name(self) -> str:
        return "failing"

    async def fetch_jobs(
        self,
        query: str,
        *,
        location: str | None = None,
        page: int = 1,
        limit: int = 20,
    ) -> list[JobSummary]:
        raise ProviderError("upstream is down")


async def test_health(client: httpx.AsyncClient) -> None:
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_search_mock_returns_scored_items(client: httpx.AsyncClient) -> None:
    response = await client.get("/jobs/search", params={"query": "python"})
    assert response.status_code == 200
    items = response.json()
    assert {item["id"] for item in items} == {"mock-1", "mock-4", "mock-8", "mock-9"}
    for item in items:
        assert {"scam_score", "is_suspicious", "flags", "title", "url"} <= item.keys()
    by_id = {item["id"]: item for item in items}
    assert by_id["mock-1"]["scam_score"] == 0
    assert by_id["mock-4"]["flags"][0]["code"] == "unrealistic_salary"


@pytest.mark.parametrize(
    ("exclude_scams", "expect_suspicious_present"),
    [
        pytest.param("true", False, id="exclude"),
        pytest.param("false", True, id="keep"),
    ],
)
async def test_exclude_scams(
    client: httpx.AsyncClient, exclude_scams: str, expect_suspicious_present: bool
) -> None:
    response = await client.get(
        "/jobs/search", params={"query": "e", "exclude_scams": exclude_scams}
    )
    assert response.status_code == 200
    ids = {item["id"] for item in response.json()}
    assert (SUSPICIOUS_IDS <= ids) is expect_suspicious_present
    assert len(ids) == (9 if expect_suspicious_present else 7)


async def test_search_persists_all_jobs_even_when_excluded(
    client: httpx.AsyncClient, session: AsyncSession
) -> None:
    await client.get("/jobs/search", params={"query": "e", "exclude_scams": "true"})
    await client.get("/jobs/search", params={"query": "e", "exclude_scams": "true"})
    count = await session.scalar(select(func.count()).select_from(JobRow))
    assert count == 9


@pytest.mark.parametrize(
    "params",
    [
        pytest.param({"query": "python", "limit": 0}, id="limit-0"),
        pytest.param({"query": "python", "limit": 51}, id="limit-51"),
        pytest.param({"query": "python", "page": 0}, id="page-0"),
        pytest.param({"query": "python", "page": 101}, id="page-101"),
        pytest.param({"query": "python", "source": "foo"}, id="unknown-source"),
        pytest.param({"query": ""}, id="empty-query"),
        pytest.param({}, id="missing-query"),
    ],
)
async def test_validation_errors(client: httpx.AsyncClient, params: dict[str, object]) -> None:
    response = await client.get("/jobs/search", params=params)
    assert response.status_code == 422


async def test_provider_error_returns_502(client: httpx.AsyncClient) -> None:
    app.dependency_overrides[get_provider] = lambda: FailingProvider()
    response = await client.get("/jobs/search", params={"query": "python"})
    assert response.status_code == 502
    assert response.json() == {"detail": "Job provider 'failing' failed: upstream is down"}


@respx.mock
async def test_adzuna_http_error_returns_502_without_leaking_keys(
    client: httpx.AsyncClient,
) -> None:
    secret = "fake-secret-key"
    app.dependency_overrides[get_provider] = lambda: AdzunaProvider(
        app_id="fake-id", app_key=secret, country="es"
    )
    route = respx.get(f"{BASE_URL}/es/search/1").mock(return_value=httpx.Response(500))
    response = await client.get("/jobs/search", params={"query": "python", "source": "adzuna"})
    assert route.called
    assert response.status_code == 502
    assert response.json()["detail"] == "Job provider 'adzuna' failed: Adzuna returned HTTP 500."
    assert secret not in response.text


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        pytest.param("mock", MockProvider, id="mock"),
        pytest.param("adzuna", AdzunaProvider, id="adzuna"),
    ],
)
def test_get_provider_selects_by_source(source: str, expected: type[JobProvider]) -> None:
    assert isinstance(get_provider(source), expected)  # type: ignore[arg-type]


async def test_lifespan_creates_tables_and_disposes_engine(
    monkeypatch: pytest.MonkeyPatch, engine: AsyncEngine
) -> None:
    monkeypatch.setattr(main, "engine", engine)
    async with main.lifespan(FastAPI()):
        pass


def test_get_detector_returns_default_detector() -> None:
    assert isinstance(get_detector(), ScamDetector)
