from typing import Any

from sqlalchemy import delete, func, select, update

from lib.db import session_scope
from models.tables import environment_measurements, fao_areas


def clean(doc: dict[str, Any]) -> dict[str, Any]:
    return dict(doc)


AREA_WITHOUT_GEOMETRY = [
    column for column in fao_areas.c
    if column.name not in {"geometry", "geometry_overview"}
]


async def list_areas(query: dict[str, Any]) -> list[dict[str, Any]]:
    stmt = select(*AREA_WITHOUT_GEOMETRY).order_by(fao_areas.c.code.asc()).limit(1000)
    if query.get("parent_code") is not None:
        stmt = stmt.where(fao_areas.c.parent_code == query["parent_code"])
    if query.get("level") is not None:
        stmt = stmt.where(fao_areas.c.level == query["level"])
    async with session_scope() as session:
        return [clean(dict(row)) for row in (await session.execute(stmt)).mappings().all()]


async def get_area(code: str) -> dict[str, Any] | None:
    stmt = select(*AREA_WITHOUT_GEOMETRY).where(fao_areas.c.code == code)
    async with session_scope() as session:
        row = (await session.execute(stmt)).mappings().first()
        return clean(dict(row)) if row else None


async def get_area_record(code: str) -> dict[str, Any] | None:
    async with session_scope() as session:
        row = (await session.execute(select(fao_areas).where(fao_areas.c.code == code))).mappings().first()
        return clean(dict(row)) if row else None


async def get_geometry(code: str) -> dict[str, Any] | None:
    stmt = select(fao_areas.c.geometry, fao_areas.c.source_name, fao_areas.c.source_url).where(fao_areas.c.code == code)
    async with session_scope() as session:
        row = (await session.execute(stmt)).mappings().first()
        return clean(dict(row)) if row else None


async def overview(query: dict[str, Any]) -> list[dict[str, Any]]:
    stmt = select(fao_areas.c.code, fao_areas.c.name_it, fao_areas.c.level, fao_areas.c.geometry_overview)
    if query.get("parent_code") is not None:
        stmt = stmt.where(fao_areas.c.parent_code == query["parent_code"])
    else:
        stmt = stmt.where(fao_areas.c.level == query.get("level", 1))
    stmt = stmt.where(fao_areas.c.geometry_overview.is_not(None))
    async with session_scope() as session:
        return [clean(dict(row)) for row in (await session.execute(stmt)).mappings().all()]


async def measurements(code: str) -> list[dict[str, Any]]:
    parts = code.split(".")
    area_codes = [".".join(parts[:index]) for index in range(len(parts), 0, -1)]
    stmt = (select(environment_measurements)
            .where(environment_measurements.c.fao_area_code.in_(area_codes))
            .order_by(environment_measurements.c.measurement_date.desc())
            .limit(500))
    async with session_scope() as session:
        return [clean(dict(row)) for row in (await session.execute(stmt)).mappings().all()]


async def count_areas() -> int:
    async with session_scope() as session:
        value = await session.scalar(select(func.count(fao_areas.c.id)))
        return int(value or 0)


async def count_measurements(source: str | None = None) -> int:
    async with session_scope() as session:
        stmt = select(func.count(environment_measurements.c.id))
        if source:
            stmt = stmt.where(environment_measurements.c.source == source)
        value = await session.scalar(stmt)
        return int(value or 0)


async def replace_measurements(area_code: str, source: str, docs: list[dict[str, Any]]) -> None:
    """Replace one source snapshot while preserving old data on fetch errors."""
    unique_docs = list({str(doc["id"]): doc for doc in docs if doc.get("id")}.values())
    async with session_scope() as session:
        await session.execute(delete(environment_measurements).where(
            environment_measurements.c.fao_area_code == area_code,
            environment_measurements.c.source == source,
        ))
        if unique_docs:
            await session.execute(environment_measurements.insert(), unique_docs)


async def upsert_area(payload: dict[str, Any]) -> str:
    async with session_scope() as session:
        existing = (await session.execute(select(fao_areas.c.id).where(fao_areas.c.code == payload["code"]))).first()
        if existing:
            await session.execute(update(fao_areas).where(fao_areas.c.code == payload["code"]).values(**payload))
            return "updated"
        await session.execute(fao_areas.insert().values(**payload))
        return "inserted"
