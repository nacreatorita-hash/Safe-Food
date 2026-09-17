"""Entry point for the single ingestion/scheduler worker."""

import asyncio

from services.ingestion.scheduler import run_scheduler


if __name__ == "__main__":
    asyncio.run(run_scheduler())
