"""Manual check: fetch a few Adzuna jobs once and print their ScamReport.

Run from the project root: python scripts/try_adzuna.py [query]
Requires ADZUNA_APP_ID / ADZUNA_APP_KEY in .env.
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from job_filter.adapters.adzuna import AdzunaProvider, ProviderError  # noqa: E402
from job_filter.core.scam_detector import ScamDetector  # noqa: E402


async def main(query: str) -> None:
    try:
        jobs = await AdzunaProvider().fetch_jobs(query, limit=5)
    except ProviderError as exc:
        print(f"Provider error: {exc}")
        return
    detector = ScamDetector()
    for job in jobs:
        report = detector.analyze(job)
        flags = ", ".join(f.code for f in report.flags) or "none"
        print(f"{job.title} | {job.company or '(no company)'} | score={report.score} | flags: {flags}")
    print(f"{len(jobs)} job(s).")


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else "python developer"))
