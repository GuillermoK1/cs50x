"""Server-rendered HTML UI (Jinja2). Job text is untrusted: autoescape stays on."""

from collections.abc import Callable
from pathlib import Path
from typing import Annotated
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from job_filter.adapters.base import JobProvider, ProviderError
from job_filter.api.dependencies import (
    SOURCES,
    Source,
    get_detector,
    get_provider_factory,
    get_repository,
    is_source,
)
from job_filter.api.schemas import JobResult
from job_filter.api.search import provider_error_message, run_search
from job_filter.core.repository import JobRepository
from job_filter.core.scam_detector import ScamDetector

PAGE = 1
LIMIT = 20

router = APIRouter()
templates = Jinja2Templates(directory=Path(__file__).parent / "templates")


def is_safe_url(url: object) -> bool:
    """True only for http/https URLs; anything else must not become a link."""
    return urlparse(str(url)).scheme in ("http", "https")


def badge_class(result: JobResult) -> str:
    """CSS class of the score badge: red (suspicious), amber (some flags) or green."""
    if result.is_suspicious:
        return "red"
    return "amber" if result.scam_score > 0 else "green"


def format_salary(result: JobResult) -> str:
    """Human-readable salary range, or an empty string when unknown."""
    values = (result.salary_min, result.salary_max)
    amounts = [f"{value:,.0f}" for value in values if value is not None]
    if not amounts:
        return ""
    unique = list(dict.fromkeys(amounts))
    return f"{' - '.join(unique)} {result.currency or ''}".strip()


templates.env.globals.update(
    is_safe_url=is_safe_url, badge_class=badge_class, format_salary=format_salary
)


@router.get("/", response_class=HTMLResponse)
async def index(
    request: Request,
    provider_factory: Annotated[Callable[[Source], JobProvider], Depends(get_provider_factory)],
    detector: Annotated[ScamDetector, Depends(get_detector)],
    repository: Annotated[JobRepository, Depends(get_repository)],
    query: str | None = None,
    source: str = "mock",
    location: str | None = None,
    exclude_scams: bool = False,
) -> HTMLResponse:
    """Search form; runs the same search flow as ``/jobs/search`` when ``query`` is given."""
    context: dict[str, object] = {
        "query": query or "",
        "source": source,
        "location": location or "",
        "exclude_scams": exclude_scams,
        "sources": SOURCES,
        "searched": False,
        "results": [],
        "error": None,
    }
    status_code = 200

    if query is not None:
        if not query.strip():
            context["error"] = "Please enter a search query."
            status_code = 400
        elif not is_source(source):
            context["error"] = f"Unknown source '{source}'."
            status_code = 400
        else:
            provider = provider_factory(source)
            try:
                context["results"] = await run_search(
                    provider,
                    detector,
                    repository,
                    query=query.strip(),
                    location=location.strip() if location and location.strip() else None,
                    page=PAGE,
                    limit=LIMIT,
                    exclude_scams=exclude_scams,
                )
                context["searched"] = True
            except ProviderError as exc:
                context["error"] = provider_error_message(provider, exc)
                status_code = 502

    return templates.TemplateResponse(request, "index.html", context, status_code=status_code)
