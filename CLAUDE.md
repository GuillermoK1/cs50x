# CS50x Final Project: Generic Job Listing Filter

Consumes job APIs via the Adapter pattern and filters suspicious listings (scams, ghost jobs).

## Stack and style
- Python 3.11+, Pydantic v2 (+ pydantic-settings), full type hints.
- Data fetching is async (`async def`, httpx).
- Short docstrings, descriptive names, no unnecessary logic.

## Layout
- `src/job_filter/{adapters,core,api,tests}`

## Architecture
- Adapter pattern: `JobProvider` ABC in `adapters/base.py`.
- `JobSummary` is the ONLY unified model. Native API models live inside each adapter, which translates them to `JobSummary`.
- Do not change existing signatures without proposing the minimal change and waiting for approval.

## Security
- Never put real keys in code or tests. Use `.env` (see `.env.example`).

## Testing
- pytest + pytest-asyncio (`asyncio_mode = "auto"`) + respx. No real network calls.
- Inject `now` for anything time-dependent; never call `datetime.now()` inside rules.
- Run `pytest` before reporting.

## Workflow
- When starting a phase: read the existing files and summarize your understanding before coding.
- Scope discipline: work only on the current phase (see `prompt_agente_faseN.md`).

## Future-phase notes (do not act early)
- Persistence: SQLAlchemy 2.0 + aiosqlite.
- Endpoint: `GET /jobs/search?query=python&exclude_scams=true`.
- Jinja2 is installed separately.
- CS50x delivery: README >= 750 words, video <= 3 min (verify on the CS50x site).
- README limitations to mention: detector false positives and Adzuna truncated text.
