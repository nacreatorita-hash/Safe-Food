"""Deduplication on (source, source_id); updates in place when the content hash changes."""

from typing import Any, Literal

import uuid
from datetime import datetime, timezone

from lib.db import session_scope
from models.schemas import Recall
from models.tables import recall_versions, recalls
from repositories.recalls import find_by_source

Outcome = Literal["inserted", "updated", "unchanged"]


def _json_safe(value: Any) -> Any:
    """Convert database-native values before storing a JSONB version snapshot."""
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    return value


async def upsert_recall(recall: Recall) -> Outcome:
    existing = await find_by_source(recall.source, recall.source_id)
    if existing is None:
        async with session_scope() as session:
            await session.execute(recalls.insert().values(**recall.model_dump()))
        return "inserted"
    if existing.get("content_hash") == recall.content_hash:
        # Enrichment bookkeeping (for example the OCR-completed marker) can
        # change without changing the canonical content hash. Persist it so
        # the rolling backfill can advance instead of selecting the same IDs
        # forever.
        incoming_fields = recall.official_fields
        if existing.get("official_fields") != incoming_fields:
            async with session_scope() as session:
                await session.execute(recalls.update().where(recalls.c.id == existing["id"]).values(
                    official_fields=incoming_fields,
                    retrieved_at=recall.retrieved_at,
                ))
            return "updated"
        return "unchanged"
    # keep a version trail instead of creating a duplicate record
    payload = recall.model_dump()
    payload["id"] = existing["id"]
    async with session_scope() as session:
        await session.execute(recall_versions.insert().values(
            version_id=str(uuid.uuid4()), recall_id=existing["id"], source=existing.get("source"),
            source_id=existing.get("source_id"), snapshot=_json_safe(existing),
            created_at=datetime.now(timezone.utc),
        ))
        await session.execute(recalls.update().where(recalls.c.id == existing["id"]).values(**payload))
    return "updated"
