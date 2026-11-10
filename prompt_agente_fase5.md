# CS50x Final Project: Generic Job Listing Filter

## Current state

**Phases 1 to 4 are complete and committed**: providers (`MockProvider`, `AdzunaProvider`, `ProviderError` in `adapters/base.py`), `ScamDetector` (`analyze`, `analyze_many`, `filter`), async SQLite persistence (`core/database.py`, `models.py`, `repository.py`), FastAPI app (`api/main.py`, `routes.py`, `dependencies.py`, `schemas.py`) with `GET /jobs/search` and `GET /health`, offline tests, coverage >= 95%.

Now we work **exclusively on Phase 5**: a simple Jinja2 web UI, the README, and the video script. This is the last phase.

**Do not implement:** new detector rules, new providers, authentication, JavaScript frameworks, or schema changes to `JobSummary`.

## Before writing code

1. Read `CLAUDE.md`, `api/`, `core/repository.py`, `tests/conftest.py`, `pyproject.toml`, `requirements.txt`.
2. Run `python -m pytest` and confirm the baseline passes.
3. Summarize in 3 or 4 lines what you understand and which files you will create or modify.
4. List any signature change you need (ideally none) and any open design question (at most 3). Wait for my confirmation before generating code.

## General rules

- Follow `CLAUDE.md`. Do not change existing signatures without proposing the minimal change and waiting for approval.
- **Never run the `live` test or call the real Adzuna API.** Use `MockProvider` or respx.
- Present each file with its full path. Return a brief summary at the end, no code dumps.

## Design constraints (decided)

- Server-side rendered with Jinja2 inside the same FastAPI app. No SPA, no build step, plain CSS (one small static file or an inline `<style>`).
- **Do not duplicate the search flow.** The HTML route must reuse the same fetch -> analyze -> persist logic as `GET /jobs/search`. If that needs extracting a shared function from `api/routes.py`, propose the minimal refactor first.
- Add `jinja2` to `requirements.txt`.
- **Security:** job titles and descriptions are untrusted third-party text. Keep Jinja2 autoescape ON, never use `|safe`, and render links only when the URL scheme is http or https, with `rel="noopener noreferrer nofollow"`.

## Tasks

### 1. UI (`api/templates/`, `api/web.py` or similar)

- `GET /` : search form (query, source `mock`/`adzuna`, location, exclude-scams checkbox) and, when submitted, the results.
- Each result shows title, company, location, salary (mark predicted salaries), posted date, a link to the offer, a score badge (green / amber / red by `scam_score`), and the flags with their reasons.
- Show a note on truncated descriptions (`description_truncated`).
- Friendly error and empty states: provider failure (the same curated message as the API's 502), no results, invalid input.
- Base template plus a results partial. Keep it simple.

### 2. Tests

- Keep all existing tests passing and coverage >= 95%.
- Cover: the page renders; results for the mock source; `exclude_scams` hides suspicious jobs; provider error shows a message and does not crash; **HTML-escaping** (a job whose title contains `<script>` is rendered escaped); a non-http URL is not rendered as a link.
- Use `@pytest.mark.parametrize` with readable `ids=`. Reuse the existing in-memory DB fixtures.

### 3. README.md (>= 750 words, English)

Required sections: title, one-paragraph description, features, architecture (Adapter pattern, why `JobSummary` is the only unified model, layers), project structure (what each file does and why), design decisions and trade-offs (async, JSON column for flags, rule-based detector, upsert, dependency injection), how to install and run (venv, `.env`, `uvicorn`), how to run tests, example `curl`, and **limitations**: detector false positives/negatives (heuristics only) and Adzuna truncated descriptions. Add a short "future work" section. Do not invent features that do not exist.

### 4. Video script (`docs/video_script.md`)

A <= 3 minute script with timestamps: what the project is, a live demo (mock search, `exclude_scams`, the flags), the architecture in one diagram or file tree, and one design decision. Keep the CS50x submission in mind: the video is submitted by URL, the README must include that URL, and the project title and description are required. Verify the current requirements on the CS50x site before finalizing.

## Acceptance criteria

- `python -m pytest` passes offline, coverage >= 95%.
- `uvicorn` starts the app, and `/` in a browser shows a working search against the mock source with scores and flags.
- Untrusted text is always escaped; no `|safe`.
- README has >= 750 words (check with a word count) and mentions both limitations.
- At the end tell me: how to run the tests, how to start the server and open the UI, the README word count, and any bugs or design issues you found (report only; do not fix without approval).
