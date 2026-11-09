# CS50x Final Project: Generic Job Listing Filter

## Role

Act as a software architect expert in Python and FastAPI. We are going to build the CS50x final project: a generic system that consumes different job APIs through the **Adapter pattern** and filters suspicious listings (scams or ghost jobs).

## Technical context

- **Python 3.11 or higher.** Use modern typing syntax (`str | None`, `list[str]`, etc.).
- **Pydantic v2** and `pydantic-settings`.
- All code must be fully typed (type hints) and ready to be tested.
- Data extraction methods are **asynchronous** (`async def`).

## Phase plan (for your reference)

| Phase | Content |
|-------|---------|
| 1 | Base architecture and data models (**this is the current phase**) |
| 2 | Concrete adapters (`AdzunaProvider`, `MockProvider`) and `ScamDetector` module |
| 3 | Tests with pytest + pytest-asyncio; HTTP simulation with `respx` |
| 4 | API layer (FastAPI) and persistence (SQLite) |
| 5 | Interface (Jinja2) and delivery (README and video) |

## Scope of THIS conversation

We work **exclusively on Phase 1** and prepare the environment for Phase 3.

**Do not implement yet:** FastAPI routes, database, concrete adapters or the `ScamDetector`.

## What you must produce

### 1. Folder structure

Propose a professional folder tree that includes at least `adapters/`, `core/`, `api/` and `tests/`. Also include:

- The necessary `__init__.py` files.
- `.env.example` and `.gitignore`.
- `pyproject.toml` with the pytest configuration (see point 5).

Explain the purpose of each folder in one line.

### 2. `requirements.txt`

It must include:

- `fastapi`
- `uvicorn`
- `pydantic`
- `pydantic-settings`
- `httpx`
- `pytest`
- `pytest-asyncio`
- `respx` (to mock `httpx` calls in tests; do **not** use `responses`, which only works with `requests`)

### 3. `core/config.py`

Configuration with `pydantic-settings` (`BaseSettings`) that reads variables from `.env`. Include example fields for the credentials of an external API (for example `adzuna_app_id` and `adzuna_app_key`) with optional or safe default values. Also deliver the matching `.env.example`.

### 4. `core/schemas.py`

Unified job listing model called **`JobSummary`** (always use this name; not `JobSchema`), with Pydantic v2.

Suggested fields: `id`, `title`, `company`, `description`, `location`, `salary_min`, `salary_max`, `currency`, `url`, `posted_at`, `source` (provider name).

Minimum validations:

- `salary_min` and `salary_max` cannot be negative if present.
- If both are present, `salary_min <= salary_max`.
- `title` cannot be empty.
- `url` must be a valid URL.

Use Pydantic v2 `field_validator` / `model_validator`.

The **native input** models of each API (Adzuna's raw format, etc.) will live inside each adapter in Phase 2. State in a comment or docstring that the adapter will be responsible for translating the native format into `JobSummary`.

### 5. `adapters/base.py`

Abstract class `JobProvider` using the `abc` module (`ABC` and `@abstractmethod`):

- An abstract `async def fetch_jobs(self, query: str, ...) -> list[JobSummary]` method.
- An abstract attribute or property `name` that identifies the provider.
- Clear docstrings explaining the contract each adapter must fulfill.

### 6. Pytest environment

- `pyproject.toml` with the `[tool.pytest.ini_options]` section including `asyncio_mode = "auto"` and `testpaths = ["tests"]`.
- `tests/conftest.py` with an example fixture that returns a valid `JobSummary`.
- `tests/test_filters.py` as a skeleton: one synchronous test and one example `async` test (they can validate `JobSummary`), plus `# TODO` comments indicating where the `ScamDetector` tests will go in Phase 2/3.

## Quality criteria

- Clean code, no unnecessary logic and descriptive names.
- Brief docstrings and type hints on all functions and methods.
- Each file must be presented with its full path in a separate code block.
- At the end, explain how to install dependencies and run `pytest` to check that the skeleton works.

## Notes for later phases (do not act yet)

- Persistence: prefer SQLAlchemy 2.0 with `aiosqlite`, since `cs50.SQL` is synchronous and blocks the event loop in `async` routes.
- Planned search endpoint: `GET /jobs/search?query=python&exclude_scams=true`.
- Jinja2 requires installing `jinja2` separately (Phase 5).
- The detector's heuristic rules will produce false positives; this must be documented as a limitation in the README.
- CS50x submission requirements (verify on the course website, they may change): README of at least 750 words and a video of at most 3 minutes.

Before generating code, summarize in 3 or 4 lines how you understand the scope. If anything is ambiguous, ask at most one question.
