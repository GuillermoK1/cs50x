# CS50x Final Project: Generic Job Listing Filter

## Current state

**Phases 1 and 2 are complete and committed**: `JobProvider` (ABC), `JobSummary`, `Settings`, `MockProvider`, `AdzunaProvider` (with `ProviderError`), `ScamDetector` (6 rules, score = sum of weights capped at 100, threshold 50), `scripts/try_adzuna.py`, and 75 passing unit tests.

Now we work **exclusively on Phase 3**: extra coverage, integration tests, and CI.

**Do not implement:** FastAPI routes, database, web UI, or anything from Phases 4 and 5. Do not add new detector rules or new providers.

## Before writing code

1. Read `CLAUDE.md`, the existing source in `src/job_filter/`, all tests, and `pyproject.toml`.
2. Run `pytest` and confirm the baseline (75 passing).
3. Summarize in 3 or 4 lines what you understand and what you will create or modify.
4. Wait for my confirmation before generating code.

## General rules

- Follow `CLAUDE.md` (style, no real keys, no real network in the default test run, injected `now`).
- Do not change existing signatures. If a test reveals a bug in the source, report it and propose the minimal fix; wait for my approval before touching the source.
- Present each file with its full path.

## Tasks

### 1. Coverage measurement

- Add `pytest-cov` to `requirements.txt`.
- Configure coverage in `pyproject.toml` (source = `src/job_filter`, show missing lines).
- Report the current coverage per module and list the uncovered lines/branches **before** writing new tests.
- Set a coverage threshold (`--cov-fail-under`) that is realistic for the final number, not aspirational. Tell me what you chose and why.

### 2. Fill coverage gaps and edge cases

Add unit tests only where the coverage report or the list below shows a real gap. Do not duplicate existing tests.

- `JobSummary`: boundaries (salary 0, equal min/max, whitespace-only title, invalid URL schemes).
- `ScamDetector`:
  - rules combining on the same job (score sums, cap at 100);
  - threshold boundary (score exactly equal to the threshold);
  - naive vs timezone-aware `posted_at` and `now`;
  - keywords in both Spanish and English, mixed case and accents;
  - `filter()` with an empty list and with all jobs suspicious.
- `AdzunaProvider`:
  - `page`, `limit` and `location` are sent correctly (`page` in the path, `limit` as `results_per_page`, `location` as `where`);
  - network errors (`httpx.ConnectError`, timeout) are wrapped in `ProviderError`;
  - missing credentials raise `ProviderError`;
  - an injected client is not closed; an internally created client is closed.
- Use `@pytest.mark.parametrize` with readable `ids=`.

### 3. Integration tests (offline)

Create `tests/test_integration.py` with end-to-end flows that use **respx** (never the real API):

- `AdzunaProvider` (mocked HTTP with the fixture) → `ScamDetector.filter()` → expected jobs remain.
- `MockProvider` → `ScamDetector` → suspicious jobs are removed and clean ones kept.
- Provider failure (HTTP 500) surfaces as `ProviderError` and does not hang or leak `httpx` exceptions.
- Two providers (mock and Adzuna) can be used through the same `JobProvider` interface (contract test, parametrized).

### 4. Optional live test (skipped by default)

- Add one test marked `@pytest.mark.live` that calls the real Adzuna API with credentials from `.env`.
- Register the `live` marker in `pyproject.toml` and make the default run **exclude** it (for example `-m "not live"` in `addopts`).
- It must skip cleanly if the credentials are missing.
- Purpose: let me verify the Adzuna fields that are still unconfirmed (`salary_is_predicted` type, `max_days_old`, `count`). The test must assert the response can be translated to `JobSummary` and print nothing sensitive.

### 5. Continuous integration

- Create `.github/workflows/tests.yml`: run on push and pull request, Python 3.11 and 3.12, install `requirements.txt`, run `pytest` with coverage. No secrets, and the `live` test must not run.
- Keep it minimal: no deploys, no extra jobs.

### 6. Documentation

- Add a short "Running tests" section to `CLAUDE.md` only if the commands changed (coverage, `live` marker).
- If the folder tree changes, tell me.

## Acceptance criteria

- `pytest` passes completely offline, without real keys, and meets the coverage threshold.
- `pytest -m live` runs the real-API test when I provide my keys, and skips otherwise.
- Every new test has a clear purpose; no tests that only raise coverage without asserting behavior.
- The CI workflow is valid YAML and does not depend on secrets.
- At the end, tell me: how to run the default tests, how to run coverage, how to run the live test, and any source bugs the new tests uncovered.

## Notes for later phases (do not act yet)

- Phase 4: SQLAlchemy 2.0 with `aiosqlite` and the endpoint `GET /jobs/search?query=python&exclude_scams=true`.
- Phase 5: Jinja2 (installed separately), README of at least 750 words and a video of at most 3 minutes (verify current requirements on the CS50x site).
- The README must mention as limitations: detector false positives and Adzuna's truncated text.
