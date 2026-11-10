"""Offline end-to-end tests: providers -> ScamDetector (HTTP mocked with respx)."""

import json
from datetime import datetime, timezone
from pathlib import Path

import httpx
import pytest
import respx

from job_filter.adapters.adzuna import AdzunaProvider, ProviderError
from job_filter.adapters.base import JobProvider
from job_filter.adapters.mock import MockProvider
from job_filter.core.scam_detector import ScamDetector

FIXTURE = Path(__file__).parent / "fixtures" / "adzuna_search.json"
URL = "https://api.adzuna.com/v1/api/jobs/es/search/1"
NOW = datetime(2025, 1, 20, tzinfo=timezone.utc)


def _adzuna() -> AdzunaProvider:
    return AdzunaProvider(app_id="fake-id", app_key="fake-key", country="es")


@respx.mock
async def test_adzuna_to_detector_keeps_expected_jobs() -> None:
    respx.get(URL).respond(json=json.loads(FIXTURE.read_text(encoding="utf-8")))
    jobs = await _adzuna().fetch_jobs("python")
    kept = ScamDetector(now=lambda: NOW).filter(jobs)
    # Job 1002 has no company (score 15, below threshold); truncated text is not penalized.
    assert [j.id for j in kept] == ["1001", "1002", "1003"]


@respx.mock
async def test_adzuna_scam_listing_is_filtered_out() -> None:
    scam = {
        "id": "9",
        "title": "Easy money",
        "description": "Guaranteed earnings, pay a registration fee. Write on WhatsApp...",
        "redirect_url": "https://x.example/9",
        "company": {"display_name": "Confidential"},
    }
    respx.get(URL).respond(json={"results": [scam]})
    jobs = await _adzuna().fetch_jobs("money")
    assert len(jobs) == 1
    assert ScamDetector(now=lambda: NOW).filter(jobs) == []


async def test_mock_provider_to_detector_removes_suspicious() -> None:
    jobs = await MockProvider().fetch_jobs("")
    kept = {job.id for job in ScamDetector(now=lambda: NOW).filter(jobs)}
    assert {"mock-1", "mock-2", "mock-3"} <= kept
    assert kept.isdisjoint({"mock-5", "mock-6"})  # single-rule offers stay below threshold


@pytest.mark.parametrize(
    "failure",
    [httpx.Response(500), httpx.ConnectError("down"), httpx.ReadTimeout("slow")],
    ids=["http-500", "connect-error", "timeout"],
)
@respx.mock
async def test_provider_failures_surface_as_provider_error(
    failure: httpx.Response | Exception,
) -> None:
    route = respx.get(URL)
    if isinstance(failure, Exception):
        route.mock(side_effect=failure)
    else:
        route.mock(return_value=failure)
    with pytest.raises(ProviderError):
        await _adzuna().fetch_jobs("python")


@pytest.mark.parametrize("provider_name", ["mock", "adzuna"])
@respx.mock
async def test_providers_share_the_same_interface(provider_name: str) -> None:
    respx.get(URL).respond(json=json.loads(FIXTURE.read_text(encoding="utf-8")))
    provider: JobProvider = MockProvider() if provider_name == "mock" else _adzuna()
    jobs = await provider.fetch_jobs("python", location=None, page=1, limit=20)
    assert provider.name == provider_name
    assert jobs
    assert all(job.source == provider_name for job in jobs)
