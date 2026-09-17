"""Single-process scheduler worker.

The API process does not start this loop. Run one dedicated worker with
``python scheduler.py`` in production so multiple API workers cannot duplicate
ingestion and notifications.
"""

import asyncio
import logging
import os
from datetime import datetime, timezone

from lib.db import ensure_indexes
from repositories.sources import list_active_source_types
from services.ingestion.sync import run_source

logger = logging.getLogger("scheduler")


def _minutes(name: str, default: int) -> int:
    try:
        return max(1, int(os.environ.get(name, str(default))))
    except (TypeError, ValueError):
        return default


async def scheduler_loop() -> None:
    intervals_min = {
        "rss": _minutes("SYNC_MINISTERO_MINUTES", 30),
        "rasff": _minutes("SYNC_RASFF_MINUTES", 360),
        "wfs": _minutes("SYNC_FAO_MINUTES", 7 * 24 * 60),
        "api": _minutes("SYNC_ENVIRONMENT_MINUTES", 24 * 60),
    }
    if os.environ.get("SCHEDULER_ENABLED", "true").lower() != "true":
        logger.info("Scheduler disabilitato da SCHEDULER_ENABLED")
        return

    await ensure_indexes()
    await asyncio.sleep(15)
    while True:
        now = datetime.now(timezone.utc)
        for source in await list_active_source_types(list(intervals_min)):
            last = source.get("last_sync_at")
            if last is not None and last.tzinfo is None:
                last = last.replace(tzinfo=timezone.utc)
            due = last is None or (now - last).total_seconds() >= intervals_min[source["source_type"]] * 60
            if due:
                try:
                    result = await run_source(source)
                    logger.info("%s: %s", source["name"], result.message)
                except Exception as exc:  # keep the loop alive whatever happens
                    logger.warning("%s: %s", source["name"], exc)
        await asyncio.sleep(60)


async def run_scheduler() -> None:
    await scheduler_loop()
