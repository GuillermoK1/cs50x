# Generic Job Listing Filter

#### Video Demo: <https://youtu.be/XEvBH9zx7q4>

## Description

Generic Job Listing Filter is a small web application and JSON API that searches job listings from external providers and scores each listing with a set of heuristic rules, so that suspicious offers (scams and "ghost jobs" that were posted long ago and are probably dead) can be flagged or hidden. A user types a query, picks a source and a location, and receives a list of normalized job offers. Each offer carries a score from 0 to 100, a colored badge and the list of reasons that raised the score. The project was built for the CS50x final project, in phases: provider adapters, the scam detector, persistence, the API, and finally the web interface and this documentation.

The goal is not to be a perfect detector. The goal is a clean, testable architecture in which new job sources and new rules can be added without touching the rest of the code.

## Features

- Search jobs from two sources: a deterministic `mock` provider (used for tests and demos, no network) and the real Adzuna API.
- One unified data model, `JobSummary`, regardless of where a job comes from.
- A rule-based scam and ghost-job detector with six rules: unrealistic salary, scam phrases (English and Spanish), off-platform contact (WhatsApp, Telegram, free email), missing or generic company, very short description, and old listing.
- A score from 0 to 100 per job, a suspicious threshold (50 by default) and a human-readable reason for every triggered rule.
- An option to exclude suspicious jobs from the results.
- Every scored job is stored in a SQLite database, including the ones that were hidden from the response.
- A server-rendered HTML page at `/` and a JSON endpoint at `/jobs/search`, both using exactly the same search flow.
- A friendly error message when a provider fails, and an explicit note when a provider truncates job descriptions.

## Architecture

The core idea is the Adapter pattern. `JobProvider` (in `adapters/base.py`) is an abstract base class with a `name` property and an async `fetch_jobs` method. Every provider lives in its own adapter module and has its own native data models. For Adzuna, those are `AdzunaJob`, `AdzunaResponse` and `AdzunaNamed`, which describe the JSON exactly as Adzuna sends it. The adapter translates those native objects into `JobSummary`, and nothing outside the adapter ever sees them.

`JobSummary` is the only unified model on purpose. If the detector, the database and the UI all spoke in terms of each provider's format, adding a third provider would mean editing all of them. With a single shared model, the rest of the application is written once, and a new provider only has to implement one class. The same reasoning is why the database has its own ORM model (`JobRow`) that is kept separate from `JobSummary`: persistence details never leak into the domain model.

The code is organized in three layers:

1. **Adapters** fetch and translate data. They know about HTTP and about provider formats.
2. **Core** contains the unified model, the scam detector, configuration, and persistence. It knows nothing about HTTP routes.
3. **API** contains the FastAPI routes, dependency wiring, response models and the Jinja2 templates.

## Project structure

- `src/job_filter/adapters/base.py`: the `JobProvider` abstract class and `ProviderError`, the single exception adapters raise when anything goes wrong.
- `src/job_filter/adapters/mock.py`: `MockProvider`, nine fixed jobs (some clean, some deliberately suspicious) filtered by query and location. It makes demos and tests deterministic.
- `src/job_filter/adapters/adzuna.py`: `AdzunaProvider`, its native models and the translation to `JobSummary`. It reads credentials from settings, wraps network and parsing failures in `ProviderError`, and never includes secrets in error messages.
- `src/job_filter/core/schemas.py`: `JobSummary`, validated with Pydantic v2.
- `src/job_filter/core/scam_detector.py`: the rules, the `ScamDetector` class, and the `Flag` and `ScamReport` models. The clock is injected so that date-dependent rules are testable.
- `src/job_filter/core/config.py`: settings loaded from environment variables and `.env`.
- `src/job_filter/core/database.py`, `models.py`, `repository.py`: async SQLAlchemy engine and sessions, the `JobRow` table, and `JobRepository`, which saves scored jobs and maps between rows and domain objects.
- `src/job_filter/api/main.py`: the FastAPI application, startup table creation, and the `/health` endpoint.
- `src/job_filter/api/routes.py`: the JSON endpoint `GET /jobs/search`.
- `src/job_filter/api/web.py` and `api/templates/`: the HTML page at `GET /`, with a base template, the search page and a partial that renders the results.
- `src/job_filter/api/search.py`: `run_search`, the single fetch, analyze, persist and filter flow shared by the JSON endpoint and the HTML page, plus the curated provider error message.
- `src/job_filter/api/dependencies.py` and `schemas.py`: overridable dependencies and the `JobResult` response model, which is a `JobSummary` plus its score and flags.
- `tests/`: offline tests for providers, detector, repository, API and web UI. `tests/fixtures/` holds a recorded Adzuna response.
- `scripts/try_adzuna.py`: a manual script to try the real Adzuna API once.
- `.github/workflows/tests.yml`: runs the test suite on every push.

## Design decisions and trade-offs

**Async everywhere that does I/O.** Fetching jobs is network-bound, so providers use `httpx` with `async def`, and the database uses SQLAlchemy 2.0 with `aiosqlite`. The price is that tests need `pytest-asyncio`, which is configured in automatic mode.

**Flags stored in a JSON column.** Each job has a variable number of flags. A separate table would be more normalized, but it would add joins and a second model for little benefit, since flags are only ever read together with their job. A JSON column keeps the schema to one table.

**A rule-based detector instead of machine learning.** Rules are transparent: each flag comes with a reason a user can read and dispute. They need no training data, and they are easy to unit test. The cost is accuracy, described in the limitations section.

**Upsert with `merge`.** The same job will appear in many searches. The primary key is the pair (source, id), and `session.merge` inserts new rows and updates existing ones, so searching twice never duplicates data. All scored jobs are saved, even those excluded from the response, so the database is a complete record of what was analyzed.

**Dependency injection.** The provider, the detector and the repository are FastAPI dependencies, so tests can replace them. The web page uses a small provider factory dependency instead of a typed `source` parameter: the page validates the source itself so that a bad value re-renders the form with a message instead of an automatic validation error.

**One search flow, two front ends.** Extracting `run_search` means the JSON API and the HTML page cannot drift apart.

**Untrusted text.** Job titles and descriptions come from third parties. Jinja2 autoescaping stays on, the `safe` filter is never used, and a job URL becomes a link only if its scheme is `http` or `https`, with `rel="noopener noreferrer nofollow"`.

## Installation and running

```
python -m venv .venv
.venv\Scripts\activate          # Windows; on Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # Windows: copy .env.example .env
```

The `mock` source works without any keys. To use Adzuna, put your own `ADZUNA_APP_ID` and `ADZUNA_APP_KEY` in `.env`. That file is ignored by git, and no real keys should ever be placed in code or tests.

Start the server from the project root:

```
python -m uvicorn job_filter.api.main:app --app-dir src --reload
```

Then open `http://127.0.0.1:8000/` in a browser. The first start creates a local `jobs.db` SQLite file.

### Running on cs50.dev

The CS50 codespace already ships Python 3, so no virtual environment is needed. In its terminal:

```
cd ~
git clone https://github.com/GuillermoK1/cs50x.git job-filter
cd job-filter
pip install -r requirements.txt
cp .env.example .env
python -m pytest
python -m uvicorn job_filter.api.main:app --app-dir src --reload
```

When VS Code reports that port 8000 is available, click **Open in Browser** (or open the **Ports** tab and click the globe icon next to 8000). The forwarded `https://...-8000.app.github.dev` address replaces `http://127.0.0.1:8000` in the browser; `curl` inside the codespace terminal still uses `127.0.0.1`.

Example JSON request:

```
curl "http://127.0.0.1:8000/jobs/search?query=python&source=mock&exclude_scams=true"
```

## Running the tests

```
python -m pytest
```

The default run is fully offline: HTTP is mocked with `respx`, the database is in memory, and the live Adzuna test is excluded. Coverage is measured automatically and the run fails below 95%. The live test, which needs real keys in `.env`, can be run on purpose with `python -m pytest -m live -o addopts="" -s`.

## Limitations

- **False positives and false negatives.** The detector uses simple heuristics. A legitimate job with a very high salary, a short description or a company that wants to stay confidential can be flagged, and a well-written scam can score zero. Treat the score as a hint, not as a verdict.
- **Adzuna truncated descriptions.** Adzuna's search API returns only a snippet of each description. The adapter marks these jobs as truncated, the short-description rule is skipped for them, and the keyword rules only see the snippet. Suspicious phrases that appear later in the full text will be missed, and the interface shows a note on these listings.

Other limits: only two sources exist, the web page always shows the first page of 20 results, and there is no authentication or user accounts.

## Future work

Possible next steps are pagination in the interface, more providers, tunable rule weights from the page, and a way for users to report wrong flags so the rules can be improved.

## Use of AI tools

AI assistance was used while building this project, as allowed by the CS50x rules.
