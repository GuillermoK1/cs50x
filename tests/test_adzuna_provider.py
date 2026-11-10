"""Tests for AdzunaProvider (no real network)."""

import json
from pathlib import Path

import httpx
import pytest
import respx

from job_filter.adapters.adzuna import AdzunaProvider
from job_filter.adapters.base import ProviderError

FIXTURE = Path(__file__).parent / "fixtures" / "adzuna_search.json"
URL = "https://api.adzuna.com/v1/api/jobs/es/search/1"


def _provider(**kwargs: object) -> AdzunaProvider:
    return AdzunaProvider(app_id="fake-id", app_key="fake-key", country="es", **kwargs)  # type: ignore[arg-type]


@respx.mock
async def test_normalizes_fixture() -> None:
    respx.get(URL).respond(json=json.loads(FIXTURE.read_text(encoding="utf-8")))
    jobs = await _provider().fetch_jobs("python")
    assert [j.id for j in jobs] == ["1001", "1002", "1003"]  # 1004 has no URL: skipped
    first = jobs[0]
    assert first.company == "Acme Software"
    assert first.location == "Madrid"
    assert str(first.url) == "https://www.adzuna.es/land/ad/1001"
    assert first.posted_at is not None
    assert first.source == "adzuna"
    assert first.description_truncated is True
    assert first.salary_is_predicted is False
    assert (first.salary_min, first.salary_max) == (40000, 55000)


@respx.mock
async def test_missing_optional_fields_become_none() -> None:
    respx.get(URL).respond(json=json.loads(FIXTURE.read_text(encoding="utf-8")))
    job = (await _provider().fetch_jobs("python"))[1]
    assert job.company == ""
    assert job.location is None
    assert job.description is None
    assert job.salary_min is None and job.posted_at is None
    assert job.description_truncated is True


@respx.mock
async def test_predicted_salary_is_kept_and_flagged() -> None:
    respx.get(URL).respond(json=json.loads(FIXTURE.read_text(encoding="utf-8")))
    job = (await _provider().fetch_jobs("python"))[2]
    assert job.salary_is_predicted is True
    assert job.salary_min == 30000


@pytest.mark.parametrize(
    ("raw", "expected"),
    [("0", False), ("1", True), (0, False), (1, True), (True, True), (False, False)],
    ids=["str-0", "str-1", "int-0", "int-1", "bool-true", "bool-false"],
)
@respx.mock
async def test_salary_is_predicted_formats(raw: object, expected: bool) -> None:
    offer = {"id": "1", "title": "T", "redirect_url": "https://x.example/1", "salary_is_predicted": raw}
    respx.get(URL).respond(json={"count": 1, "results": [offer]})
    assert (await _provider().fetch_jobs("t"))[0].salary_is_predicted is expected


@respx.mock
async def test_empty_response() -> None:
    respx.get(URL).respond(json={"count": 0, "results": []})
    assert await _provider().fetch_jobs("nothing") == []


@pytest.mark.parametrize("status", [401, 500], ids=["unauthorized", "server-error"])
@respx.mock
async def test_http_errors_raise_provider_error(status: int) -> None:
    respx.get(URL).respond(status_code=status)
    with pytest.raises(ProviderError, match=str(status)):
        await _provider().fetch_jobs("python")


@pytest.mark.parametrize(
    "body",
    ["not json", '{"unexpected": 1}', '{"results": "nope"}'],
    ids=["not-json", "no-results", "wrong-shape"],
)
@respx.mock
async def test_malformed_payload_raises_provider_error(body: str) -> None:
    respx.get(URL).respond(content=body)
    with pytest.raises(ProviderError):
        await _provider().fetch_jobs("python")


@respx.mock
async def test_network_error_is_wrapped() -> None:
    respx.get(URL).mock(side_effect=httpx.ConnectError("boom"))
    with pytest.raises(ProviderError):
        await _provider().fetch_jobs("python")


async def test_missing_credentials_raise_provider_error() -> None:
    provider = AdzunaProvider(app_id=None, app_key=None, country="es")
    provider._app_id = provider._app_key = None  # ignore any local .env
    with pytest.raises(ProviderError, match="credentials"):
        await provider.fetch_jobs("python")


@respx.mock
async def test_request_params_are_sent() -> None:
    route = respx.get(URL).respond(json={"results": []})
    await _provider(max_days_old=30).fetch_jobs("python dev", location="madrid", limit=5)
    params = route.calls.last.request.url.params
    assert params["app_id"] == "fake-id"
    assert params["app_key"] == "fake-key"
    assert params["what"] == "python dev"
    assert params["where"] == "madrid"
    assert params["results_per_page"] == "5"
    assert params["max_days_old"] == "30"


@respx.mock
async def test_optional_params_omitted_when_unset() -> None:
    route = respx.get(URL).respond(json={"results": []})
    await _provider().fetch_jobs("python")
    params = route.calls.last.request.url.params
    assert "where" not in params and "max_days_old" not in params


@respx.mock
async def test_injected_client_is_not_closed() -> None:
    respx.get(URL).respond(json={"results": []})
    async with httpx.AsyncClient() as client:
        await _provider(client=client).fetch_jobs("python")
        assert not client.is_closed


# --- Phase 3: gap tests ---


def test_provider_name() -> None:
    assert _provider().name == "adzuna"


@respx.mock
async def test_page_goes_in_path_and_limit_is_results_per_page() -> None:
    route = respx.get("https://api.adzuna.com/v1/api/jobs/es/search/3").respond(json={"results": []})
    await _provider().fetch_jobs("python", page=3, limit=7, location="Sevilla")
    request = route.calls.last.request
    assert request.url.path.endswith("/search/3")
    assert request.url.params["results_per_page"] == "7"
    assert request.url.params["where"] == "Sevilla"


@respx.mock
async def test_timeout_is_wrapped() -> None:
    respx.get(URL).mock(side_effect=httpx.ReadTimeout("slow"))
    with pytest.raises(ProviderError, match="ReadTimeout"):
        await _provider().fetch_jobs("python")


@respx.mock
async def test_internal_client_is_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    created: list[httpx.AsyncClient] = []
    original = httpx.AsyncClient

    def tracking_client(*args: object, **kwargs: object) -> httpx.AsyncClient:
        client = original(*args, **kwargs)  # type: ignore[arg-type]
        created.append(client)
        return client

    monkeypatch.setattr(httpx, "AsyncClient", tracking_client)
    respx.get(URL).respond(json={"results": []})
    await _provider().fetch_jobs("python")
    assert len(created) == 1 and created[0].is_closed


@respx.mock
async def test_null_predicted_flag_defaults_to_false() -> None:
    offer = {"id": "1", "title": "T", "redirect_url": "https://x.example/1", "salary_is_predicted": None}
    respx.get(URL).respond(json={"results": [offer]})
    assert (await _provider().fetch_jobs("t"))[0].salary_is_predicted is False


@respx.mock
async def test_offer_failing_jobsummary_validation_is_skipped() -> None:
    good = {"id": "1", "title": "Ok", "redirect_url": "https://x.example/1"}
    bad_url = {"id": "2", "title": "Bad", "redirect_url": "not-a-url"}
    inverted = {
        "id": "3", "title": "Inv", "redirect_url": "https://x.example/3",
        "salary_min": 9, "salary_max": 1,
    }
    respx.get(URL).respond(json={"results": [bad_url, good, inverted]})
    assert [j.id for j in await _provider().fetch_jobs("t")] == ["1"]
