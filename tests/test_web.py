"""HTML UI tests: rendering, filtering, errors, escaping and link safety (no network)."""

from collections.abc import Callable
from datetime import datetime, timezone

import httpx
import pytest

from job_filter.adapters.base import JobProvider, ProviderError
from job_filter.api import web
from job_filter.api.dependencies import get_provider_factory
from job_filter.api.main import app
from job_filter.api.schemas import JobResult
from job_filter.core.schemas import JobSummary

SUSPICIOUS_TITLES = ("Home Assistant", "Remote Data Entry")  # mock-5 and mock-6


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


class StaticProvider(JobProvider):
    """Provider returning a fixed list of jobs."""

    def __init__(self, jobs: list[JobSummary]) -> None:
        self._jobs = jobs

    @property
    def name(self) -> str:
        return "static"

    async def fetch_jobs(
        self,
        query: str,
        *,
        location: str | None = None,
        page: int = 1,
        limit: int = 20,
    ) -> list[JobSummary]:
        return self._jobs


def _result(**overrides: object) -> JobResult:
    """Build a JobResult without validation (lets tests use otherwise blocked values)."""
    data: dict[str, object] = {
        "id": "r-1",
        "title": "Engineer",
        "company": "Acme",
        "url": "https://example.com/r-1",
        "source": "test",
        "scam_score": 0,
        "is_suspicious": False,
        "flags": [],
        "salary_is_predicted": False,
        "description_truncated": False,
    }
    return JobResult.model_construct(**(data | overrides))


async def test_index_without_query_renders_form_only(client: httpx.AsyncClient) -> None:
    response = await client.get("/")
    assert response.status_code == 200
    assert "<form" in response.text
    assert 'name="query"' in response.text
    assert "No jobs found" not in response.text
    assert 'class="card"' not in response.text


async def test_mock_results_render_scores_and_flags(client: httpx.AsyncClient) -> None:
    response = await client.get("/", params={"query": "e", "source": "mock"})
    assert response.status_code == 200
    text = response.text
    for title in ("Python Developer", *SUSPICIOUS_TITLES):
        assert title in text
    assert "badge green" in text
    assert "badge red" in text
    assert "<code>unrealistic_salary</code>" in text
    assert "<code>scam_keywords</code>" in text
    assert 'rel="noopener noreferrer nofollow"' in text
    assert "EUR" in text


async def test_form_values_are_kept_on_rerender(client: httpx.AsyncClient) -> None:
    response = await client.get(
        "/",
        params={"query": "python", "location": "Madrid", "exclude_scams": "on"},
    )
    assert 'value="python"' in response.text
    assert 'value="Madrid"' in response.text
    assert "checked" in response.text


@pytest.mark.parametrize(
    ("exclude_scams", "titles_visible"),
    [
        pytest.param({"exclude_scams": "on"}, False, id="exclude-on"),
        pytest.param({}, True, id="exclude-off"),
    ],
)
async def test_exclude_scams_hides_suspicious_titles(
    client: httpx.AsyncClient, exclude_scams: dict[str, str], titles_visible: bool
) -> None:
    response = await client.get("/", params={"query": "e"} | exclude_scams)
    assert response.status_code == 200
    for title in SUSPICIOUS_TITLES:
        assert (title in response.text) is titles_visible


@pytest.mark.parametrize(
    ("params", "message"),
    [
        pytest.param({"query": ""}, "Please enter a search query.", id="empty-query"),
        pytest.param({"query": "   "}, "Please enter a search query.", id="blank-query"),
        pytest.param({"query": "python", "source": "foo"}, "Unknown source", id="bad-source"),
    ],
)
async def test_invalid_input_returns_400_and_form(
    client: httpx.AsyncClient, params: dict[str, str], message: str
) -> None:
    response = await client.get("/", params=params)
    assert response.status_code == 400
    assert message in response.text
    assert "<form" in response.text


async def test_provider_error_shows_message(client: httpx.AsyncClient) -> None:
    app.dependency_overrides[get_provider_factory] = lambda: lambda source: FailingProvider()
    response = await client.get("/", params={"query": "python"})
    assert response.status_code == 502
    assert "Job provider &#39;failing&#39; failed: upstream is down" in response.text
    assert "<form" in response.text


async def test_no_results_shows_empty_message(client: httpx.AsyncClient) -> None:
    response = await client.get("/", params={"query": "zzzzzz-no-match"})
    assert response.status_code == 200
    assert "No jobs found" in response.text


async def test_blank_location_is_ignored(client: httpx.AsyncClient) -> None:
    response = await client.get("/", params={"query": "python", "location": "  "})
    assert response.status_code == 200
    assert "Python Developer" in response.text


async def test_untrusted_title_is_escaped(
    client: httpx.AsyncClient, make_job: Callable[..., JobSummary]
) -> None:
    job = make_job(title="<script>alert(1)</script>", description="x" * 60)
    app.dependency_overrides[get_provider_factory] = lambda: lambda source: StaticProvider([job])
    response = await client.get("/", params={"query": "anything"})
    assert response.status_code == 200
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in response.text
    assert "<script>alert" not in response.text


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        pytest.param("http://example.com", True, id="http"),
        pytest.param("https://example.com/a", True, id="https"),
        pytest.param("javascript:alert(1)", False, id="javascript"),
        pytest.param("ftp://example.com/file", False, id="ftp"),
        pytest.param("data:text/html,<b>x</b>", False, id="data"),
        pytest.param("", False, id="empty"),
    ],
)
def test_is_safe_url(url: str, expected: bool) -> None:
    assert web.is_safe_url(url) is expected


def test_non_http_url_is_not_rendered_as_link() -> None:
    template = web.templates.env.get_template("_results.html")
    html = template.render(results=[_result(title="Sneaky", url="javascript:alert(1)")])
    assert "Sneaky" in html
    assert "href=" not in html


def test_http_url_is_rendered_with_safe_rel() -> None:
    template = web.templates.env.get_template("_results.html")
    html = template.render(results=[_result(title="Fine")])
    assert 'href="https://example.com/r-1"' in html
    assert 'rel="noopener noreferrer nofollow"' in html


@pytest.mark.parametrize(
    ("overrides", "expected"),
    [
        pytest.param({"is_suspicious": True, "scam_score": 60}, "red", id="suspicious"),
        pytest.param({"scam_score": 15}, "amber", id="some-flags"),
        pytest.param({"scam_score": 0}, "green", id="clean"),
    ],
)
def test_badge_class(overrides: dict[str, object], expected: str) -> None:
    assert web.badge_class(_result(**overrides)) == expected


@pytest.mark.parametrize(
    ("overrides", "expected"),
    [
        pytest.param({}, "", id="unknown"),
        pytest.param(
            {"salary_min": 30000, "salary_max": 40000, "currency": "EUR"},
            "30,000 - 40,000 EUR",
            id="range",
        ),
        pytest.param({"salary_min": 30000, "salary_max": 30000}, "30,000", id="same-no-currency"),
        pytest.param({"salary_max": 40000, "currency": "USD"}, "40,000 USD", id="max-only"),
    ],
)
def test_format_salary(overrides: dict[str, object], expected: str) -> None:
    assert web.format_salary(_result(**overrides)) == expected


def test_result_card_shows_optional_details() -> None:
    template = web.templates.env.get_template("_results.html")
    html = template.render(
        results=[
            _result(
                salary_min=1,
                salary_is_predicted=True,
                description_truncated=True,
                posted_at=datetime(2026, 1, 15, tzinfo=timezone.utc),
                location="Madrid",
            )
        ]
    )
    assert "(predicted)" in html
    assert "truncated this description" in html
    assert "Madrid" in html
    assert "Posted: 2026-01-15" in html
