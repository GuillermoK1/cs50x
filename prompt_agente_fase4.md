# CS50x Final Project: Generic Job Listing Filter

## Current state

**Phases 1 to 3 are complete and committed**: `JobProvider` (ABC), `JobSummary`, `Settings`, `MockProvider`, `AdzunaProvider` (+ `ProviderError`), `ScamDetector` / `ScamReport`, offline unit and integration tests (respx), a `live` test excluded by default, CI workflow, and coverage >= 95% enforced via `addopts`.

Now we work **exclusively on Phase 4**: the FastAPI layer and SQLite persistence.

**Do not implement:** Jinja2 templates, HTML pages, README, or anything from Phase 5. Do not add detector rules or providers.

## Before writing code

1. Read `CLAUDE.md`, the source in `src/job_filter/` (especially `core/`, `adapters/`, `api/`), `pyproject.toml`, `requirements.txt`, and the test setup.
2. Run `python -m pytest` and confirm the baseline passes.
3. Summarize in 3 or 4 lines what you understand and which files you will create or modify.
4. List any signature change you need (ideally none) and any open design question (at most 3). Wait for my confirmation before generating code.

## General rules

- Follow `CLAUDE.md`. Do not change existing signatures without proposing the minimal change and waiting for approval.
- **Never run the `live` test or call the real Adzuna API.** Use `MockProvider` or respx.
- Present each file with its full path. Return a brief summary at the end, no code dumps.

## Design constraints (decided)

- **Persistence:** SQLAlchemy 2.0 (typed `Mapped[...]` style) with `aiosqlite`, fully async. Do not use `cs50.SQL` (it is synchronous and would block the event loop).
- **ORM models are separate from `JobSummary`.** `JobSummary` stays the only unified domain model; the ORM layer maps to and from it.
- The database URL comes from `Settings` (e.g. `database_url`, default `sqlite+aiosqlite:///./jobs.db`). Add it to `.env.example`. `jobs.db` must be in `.gitignore`.
- Create tables at startup with the FastAPI lifespan (`create_all`). No Alembic.
- Providers and the detector are injected with FastAPI dependencies so tests can override them.

## Tasks

### 1. Persistence layer (`core/db.py` or `core/database.py`, `core/models.py`, `core/repository.py`)

- Async engine and session factory; a session dependency.
- ORM table for jobs, keyed by (`source`, `id`), storing the `JobSummary` fields plus the scam score and flags (JSON column or related table; choose the simpler option and justify it).
- Repository with async methods, at least: `save_results(jobs, reports)` (upsert by `source` + `id`) and `list_jobs(source=None, exclude_scams=False, ...)`.
- Map ORM rows back to `JobSummary` and `ScamReport`.

### 2. API layer (`api/`)

- `api/main.py`: FastAPI app with lifespan and a router include.
- `GET /jobs/search?query=python&exclude_scams=true` with optional `source` (`mock` or `adzuna`, default `mock`), `location`, `page`, `limit` (validated bounds).
- Flow: provider `fetch_jobs` → `ScamDetector.analyze` for each job → persist → return the list.
- Response model (Pydantic): each item contains the job fields plus `scam_score`, `is_suspicious` and `flags` (code + reason). If `exclude_scams=true`, suspicious jobs are omitted.
- Error handling: `ProviderError` → HTTP 502 with a clear message; unknown `source` → 422/400; never leak keys or raw exceptions.
- `GET /health` returning a simple status.
- A dependency that builds the provider by `source`; `AdzunaProvider` is created only when requested and uses `Settings`.

### 3. Tests

Keep all existing tests passing and the coverage threshold satisfied.

- Use `httpx.AsyncClient` with `ASGITransport` (or `TestClient`) and an **in-memory SQLite** database (override the session dependency). No files left on disk.
- Cover: successful search with `MockProvider`; `exclude_scams=true` removes suspicious jobs and `false` keeps them; param validation (`limit`, `page`, bad `source`); `ProviderError` → 502 (provider overridden or Adzuna mocked with respx); `/health`.
- Persistence: upsert does not duplicate rows when the same search runs twice; stored scores/flags round-trip correctly; `list_jobs` filters.
- Use `@pytest.mark.parametrize` with readable `ids=`. Inject `now` into the detector where dates matter.

### 4. Dependencies and docs

- Add `sqlalchemy` and `aiosqlite` to `requirements.txt` (`fastapi`, `uvicorn` and `httpx` are already there).
- Update `.env.example`, `.gitignore`, and the "Running tests" / layout notes in `CLAUDE.md` only if they changed.
- Tell me how to start the server (`uvicorn ...`) and give a `curl` example I can run against the `mock` source.

## Acceptance criteria

- `python -m pytest` passes offline, with no real keys and the coverage threshold met.
- `uvicorn` starts the app and `GET /jobs/search?query=python&exclude_scams=true` returns scored results from the mock source, and they are persisted in SQLite.
- Domain code (`core/`, `adapters/`) has no FastAPI or SQLAlchemy-session imports beyond the persistence modules.
- Every error path returns a useful, non-leaky response.
- At the end tell me: how to run the tests, how to run the server, and any bugs or design issues you found in earlier phases (report only; do not fix without approval).

## Notes for later phases (do not act yet)

- Phase 5: Jinja2 (installed separately) UI, README of at least 750 words, and a video of at most 3 minutes (verify current requirements on the CS50x site).
- The README must mention as limitations: detector false positives and Adzuna's truncated text.
