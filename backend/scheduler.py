"""Entry point for the single ingestion/scheduler worker."""

import argparse
import asyncio

from services.ingestion.scheduler import run_scheduler


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Food Alert Italia ingestion scheduler")
    parser.add_argument(
        "--once",
        action="store_true",
        help="esegue una sola sincronizzazione delle fonti dovute e termina",
    )
    args = parser.parse_args()
    asyncio.run(run_scheduler(once=args.once))
