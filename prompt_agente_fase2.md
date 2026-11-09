# CS50x Final Project: Generic Job Listing Filter

## Current status

**Phase 1 is completed and committed**: `src/job_filter/` structure (with `adapters/`, `core/`, `api/`, `tests/`), `JobProvider` (ABC), `JobSummary` (Pydantic v2), `config.py` (pydantic-settings), pytest environment with `asyncio_mode = "auto"`, fixtures `valid_job` and `make_job`. 14 tests pass.

Stable project rules (stack, layout, conventions) live in `CLAUDE.md`; follow them.

We now work **exclusively on Phase 2**: concrete adapters and the filtering engine.

**Do not implement yet:** FastAPI routes, database, web interface or anything from Phases 4 and 5.

## Phase plan

| Phase | Content |
|-------|---------|
| 1 | Base architecture and data models (done) |
| 2 | Adapters (`MockProvider`, `AdzunaProvider`), `ScamDetector` and their unit tests |
| 3 | Extra coverage, integration tests, CI |
| 4 | API layer (FastAPI) and persistence (SQLAlchemy 2.0 + aiosqlite) |
| 5 | Interface (Jinja2) and delivery (README and video) |

## Suggested split of Phase 2

- **2a:** `MockProvider` + `ScamDetector` + their tests.
- **2b:** `AdzunaProvider` + its tests + `scripts/try_adzuna.py`.

**Do 2a first and wait for my OK before starting 2b.**

## Before writing code

1. Read the existing files: `adapters/base.py`, `core/schemas.py`, `core/config.py`, `tests/conftest.py`.
2. Summarize in 3 or 4 lines how you understand the scope and which files you will create or modify.
3. **Decide up front which `fetch_jobs` parameters belong in the ABC** (e.g. `location`, `page`, `limit`) **and which belong in the adapter constructor** (e.g. country, credentials, client). Present this decision to me. If `base.py` must change, propose the minimal change and wait for my approval.
4. Propose the `JobSummary` additions below and wait for my approval before adding them.
5. Wait for my confirmation before generating code.

## General rules

- Keep the Phase 1 style (brief docstrings, descriptive names).
- Do not change existing signatures without telling me and justifying it. If you need to modify `JobProvider` or `JobSummary`, propose the minimal change and wait for my approval.
- Present each file with its full path.
- Never include real keys in code or tests.

## Proposed `JobSummary` additions (ask approval first)

- `salary_is_predicted: bool = False` — True when the provider estimated the salary instead of the listing declaring it.
- `description_truncated: bool = False` — True when the provider only gives a partial description.

Both have safe defaults, so existing code and the 14 current tests must keep working unchanged.

## Tasks

### 1. `adapters/mock.py` — `MockProvider` (2a)

- Subclass of `JobProvider` with `name = "mock"`.
- Returns a fixed, deterministic list of `JobSummary`, including normal listings and several suspicious ones (to exercise the detector).
- Must respect the `fetch_jobs` signature defined in `base.py` (as agreed above).

### 2. `core/scam_detector.py` — `ScamDetector` (2a)

**Rule-based** detector, deterministic and with no external dependencies.

Design:

- A `ScamReport` model (Pydantic) with: `job_id`, `score` (0 to 100), `flags` (list of triggered rules, each with a short code and a human-readable reason) and `is_suspicious` (bool, based on a configurable threshold).
- `ScamDetector` class with an `analyze(job: JobSummary) -> ScamReport` method and a `filter(jobs: list[JobSummary]) -> list[JobSummary]` method that returns only the non-suspicious ones.
- Each rule must be a small, independent function or class with its own weight, so it can be tested in isolation and new rules can be added easily.
- **Score aggregation:** `score` is the sum of the weights of the triggered rules, capped at 100. `is_suspicious` is `score >= threshold`. The threshold is configurable (default e.g. 50). Weights are configurable with reasonable defaults.
- "Now" must be **injectable** (e.g. a `now` parameter or a callable) so date tests are deterministic. Do not call `datetime.now()` directly inside the rules.
- **Constants:** the keyword lists (Spanish and English) and the generic company names must be module-level constants defined in one single place, not scattered inside rules.

Initial rules (implement these and no more):

1. **Unrealistic salary:** extremely high salary for the type of listing, or a disproportionate min/max range. Ignore predicted salaries (`salary_is_predicted`).
2. **Scam keywords:** phrases such as upfront payment, "initial investment", "no experience, guaranteed earnings", wire transfers, cryptocurrencies.
3. **Off-platform contact:** asks to be contacted via WhatsApp, Telegram or free-domain email addresses.
4. **Missing or generic company data:** empty company or a generic company name.
5. **Empty or too-short description.** Use the `description_truncated` field: do not penalize short descriptions when `description_truncated` is True. Do **not** check `source == "adzuna"`.
6. **Old listing (possible ghost job):** `posted_at` very old relative to `now`.

Keywords must support Spanish and English. Document in docstrings that these are heuristics and may produce false positives and false negatives.

### 3. `adapters/adzuna.py` — `AdzunaProvider` (2b)

Official Adzuna API. Data verified from its documentation:

- Endpoint: `GET https://api.adzuna.com/v1/api/jobs/{country}/search/{page}`
- `country` is a two-letter code (e.g. `es`, `gb`, `us`); `page` starts at 1.
- Query parameters: `app_id` and `app_key` (required), `results_per_page`, `what` (keywords), `where` (location), `max_days_old`, `salary_min`, `what_exclude`.
- The JSON response contains a `results` list and a total `count`.
- Each listing includes, among others: `id`, `title`, `description`, `created`, `redirect_url`, `salary_min`, `salary_max`, `salary_is_predicted`, `company.display_name`, `location.display_name`.
- The description comes **truncated** and `redirect_url` goes through Adzuna. Map this to `description_truncated=True` so the detector can account for it.
- Adzuna **estimates** a salary when the listing does not state one (`salary_is_predicted`). Map it to `salary_is_predicted` and do not treat it as a declared salary.

If any field name does not match what you remember, **do not assume it**: check the official documentation (developer.adzuna.com) or tell me to verify it.

Implementation requirements:

- Use `httpx.AsyncClient`. Allow **injecting the client** through the constructor (for tests); if none is injected, create it internally and close it properly.
- Credentials and the default country come from `core/config.py` (add `adzuna_country` with default `"es"` if needed).
- In `core/config.py`, `adzuna_app_key` should be `SecretStr` (use `.get_secret_value()` only when building the request, never log it).
- Define in this same file Pydantic models for Adzuna's **native response** (e.g. `AdzunaJob`, `AdzunaResponse`) and a function or method that converts them to `JobSummary`. This translation is the adapter's core responsibility.
- If an optional field is missing in a listing, it must not break the whole batch: skip that listing or fill with `None`, and document the criterion.
- Errors: define simple custom exceptions (e.g. `ProviderError`) for network failures, non-200 HTTP status or unexpected JSON. Do not let `httpx` exceptions leak out unwrapped.
- **Rate limits:** Adzuna's free tier has rate limits. The manual script must not loop and should fetch only a few results (e.g. `results_per_page=5`).

### 4. Tests

Keep the 14 current tests passing and add:

- (2a) `tests/test_mock_provider.py`: the mock returns valid `JobSummary` objects and fulfills the `JobProvider` contract.
- (2a) `tests/test_scam_detector.py` (or `tests/test_filters.py`, whichever is tidier): at least one test per rule with a positive and a negative case (use `make_job`), threshold and score tests (including the cap at 100), and a test for `filter()`. Use an injected `now` for dates.
- (2b) `tests/test_adzuna_provider.py`: use **`respx`** to simulate the API (no real calls). Minimum cases: correct response with field normalization, empty response, HTTP errors (401 and 500), malformed JSON, listing with missing optional fields, and verification that `app_id`, `app_key`, `what` and `results_per_page` are sent in the request.
- Use `@pytest.mark.parametrize` with readable `ids=` when there are several similar cases.
- For sample Adzuna responses, store a small JSON in `tests/fixtures/` instead of embedding it in code.

### 5. Minimal documentation

- Update `.env.example` with `ADZUNA_APP_ID`, `ADZUNA_APP_KEY` and `ADZUNA_COUNTRY` (example values, not real ones).
- If the folder tree changes, point it out.

## Acceptance criteria

- `pytest` passes completely with no internet access and no real keys.
- No test calls the real Adzuna API.
- All detector rules have their own tests.
- The detector's output is explainable: each flag includes a human-readable reason.
- At the end of 2b, tell me how to run the tests and how to try the adapter manually with my real keys (a short `scripts/try_adzuna.py` that prints a few listings and their `ScamReport`, without looping).

## Notes for later phases (do not act yet)

- Phase 3: extra coverage, integration tests, CI.
- Phase 4: SQLAlchemy 2.0 with `aiosqlite` and endpoint `GET /jobs/search?query=python&exclude_scams=true`.
- Phase 5: Jinja2 (requires installing `jinja2`), README of at least 750 words and a video of at most 3 minutes (verify current requirements on the CS50x website).
- The README must mention as limitations: detector false positives and Adzuna's truncated text.
