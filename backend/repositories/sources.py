from typing import Any

from sqlalchemy import delete, func, select, update

from lib.db import session_scope
from models.tables import data_sources, environment_measurements, fao_areas, notifications, pantry_items, recalls


def clean(doc: dict[str, Any]) -> dict[str, Any]:
    return dict(doc)


async def list_sources() -> list[dict[str, Any]]:
    stmt = select(data_sources).order_by(data_sources.c.name.asc()).limit(50)
    async with session_scope() as session:
        return [clean(dict(row)) for row in (await session.execute(stmt)).mappings().all()]


async def get_source(source_id: str) -> dict[str, Any] | None:
    async with session_scope() as session:
        row = (await session.execute(select(data_sources).where(data_sources.c.id == source_id))).mappings().first()
        return clean(dict(row)) if row else None


async def list_active_source_types(types: list[str]) -> list[dict[str, Any]]:
    stmt = select(data_sources).where(data_sources.c.source_type.in_(types), data_sources.c.active.is_(True))
    async with session_scope() as session:
        return [clean(dict(row)) for row in (await session.execute(stmt)).mappings().all()]


async def upsert_source(payload: dict[str, Any]) -> None:
    async with session_scope() as session:
        existing = (await session.execute(select(data_sources.c.id).where(data_sources.c.id == payload["id"]))).first()
        if existing:
            # Seed/configuration updates must not reset runtime telemetry. In
            # particular, changing the cadence must preserve the last sync,
            # counters, errors and the durable Ministero queue.
            runtime_fields = {
                "last_sync_at", "last_successful_sync_at", "last_error",
                "record_count", "pending_count", "last_recheck_at", "pending_entries",
            }
            values = {
                key: value for key, value in payload.items()
                if key not in {"id", *runtime_fields}
            }
            await session.execute(update(data_sources).where(data_sources.c.id == payload["id"]).values(**values))
        else:
            await session.execute(data_sources.insert().values(**payload))


async def update_source(source_id: str, values: dict[str, Any]) -> None:
    async with session_scope() as session:
        await session.execute(update(data_sources).where(data_sources.c.id == source_id).values(**values))


async def pending_entries(source_id: str) -> list[dict[str, Any]]:
    source = await get_source(source_id)
    values = source.get("pending_entries", []) if source else []
    return [value for value in values if isinstance(value, dict)]


async def purge_demo() -> tuple[int, int, int]:
    async with session_scope() as session:
        recalls_deleted = (await session.execute(delete(recalls).where(recalls.c.is_demo.is_(True)))).rowcount or 0
        measurements_deleted = (await session.execute(delete(environment_measurements).where(environment_measurements.c.is_demo.is_(True)))).rowcount or 0
        pantry_deleted = (await session.execute(delete(pantry_items).where(pantry_items.c.ean.in_(["8001234567890", "8004567891234", "8001111222333"])))).rowcount or 0
        return int(recalls_deleted), int(measurements_deleted), int(pantry_deleted)


async def prune_sources(allowed_ids: list[str]) -> int:
    async with session_scope() as session:
        result = await session.execute(delete(data_sources).where(data_sources.c.id.not_in(allowed_ids)))
        return int(result.rowcount or 0)


async def overview_counts() -> dict[str, int]:
    tables = {
        "recalls": recalls,
        "pantry_items": pantry_items,
        "notifications": notifications,
        "fao_areas": fao_areas,
        "measurements": environment_measurements,
    }
    async with session_scope() as session:
        values = {name: int((await session.scalar(select(func.count(table.c.id)))) or 0) for name, table in tables.items()}
        values["recalls_to_verify"] = int((await session.scalar(select(func.count(recalls.c.id)).where(recalls.c.verified.is_(False)))) or 0)
        values["demo_recalls"] = int((await session.scalar(select(func.count(recalls.c.id)).where(recalls.c.is_demo.is_(True)))) or 0)
        return values
