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
from models.schemas import SyncResult
from repositories.sources import list_active_source_types, update_source
from services.ingestion.sync import run_source

logger = logging.getLogger("scheduler")
SOURCE_TIMEOUT_SECONDS = 180


def _minutes(name: str, default: int) -> int:
    try:
        return max(1, int(os.environ.get(name, str(default))))
    except (TypeError, ValueError):
        return default


def _intervals_min() -> dict[str, int]:
    # FAO areas are reference geometry. They are deliberately excluded from
    # the automatic scheduler and may only be refreshed by an explicit admin
    # action when the official classification changes.
    return {
        "rss": _minutes("SYNC_MINISTERO_MINUTES", 30),
        "rasff": _minutes("SYNC_RASFF_MINUTES", 360),
        "api": _minutes("SYNC_ENVIRONMENT_MINUTES", 24 * 60),
    }


def _enabled() -> bool:
    if os.environ.get("SCHEDULER_ENABLED", "true").lower() != "true":
        logger.info("Scheduler disabilitato da SCHEDULER_ENABLED")
        return False
    return True


def _source_timeout() -> float:
    try:
        return max(30.0, float(os.environ.get("SYNC_SOURCE_TIMEOUT_SECONDS", SOURCE_TIMEOUT_SECONDS)))
    except (TypeError, ValueError):
        return float(SOURCE_TIMEOUT_SECONDS)


async def _sync_due_sources(intervals_min: dict[str, int]) -> None:
    now = datetime.now(timezone.utc)
    sources = await list_active_source_types(list(intervals_min))

    for source in sources:
        last = source.get("last_sync_at")
        if last is not None and last.tzinfo is None:
            last = last.replace(tzinfo=timezone.utc)
        due = last is None or (now - last).total_seconds() >= intervals_min[source["source_type"]] * 60
        if due:
            try:
                result = await asyncio.wait_for(run_source(source), timeout=_source_timeout())
                logger.info("%s: %s", source["name"], result.message)
            except asyncio.TimeoutError:
                message = (f"{source['name']}: timeout dopo {_source_timeout():.0f} secondi; "
                           "dati precedenti mantenuti, nuovo tentativo al prossimo ciclo.")
                await update_source(source["id"], {
                    "last_sync_at": now,
                    "last_error": message,
                })
                logger.warning(message)
            except Exception as exc:  # keep the loop alive whatever happens
                logger.warning("%s: %s", source["name"], exc)


async def scheduler_loop() -> None:
    intervals_min = _intervals_min()
    if not _enabled():
        return

    await ensure_indexes()
    await asyncio.sleep(15)
    while True:
        await _sync_due_sources(intervals_min)
        await asyncio.sleep(60)


async def run_once() -> None:
    """Run only the sources whose configured interval has elapsed."""
    if not _enabled():
        return
    await ensure_indexes()
    await _sync_due_sources(_intervals_min())


async def run_scheduler(*, once: bool = False) -> None:
    if once:
        await run_once()
        return
    await scheduler_loop()
