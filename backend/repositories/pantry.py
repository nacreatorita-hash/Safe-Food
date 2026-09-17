from typing import Any

from sqlalchemy import delete, select

from lib.db import session_scope
from models.tables import pantry_items


def clean(doc: dict[str, Any]) -> dict[str, Any]:
    return dict(doc)


async def list_items() -> list[dict[str, Any]]:
    stmt = select(pantry_items).order_by(pantry_items.c.created_at.desc()).limit(200)
    async with session_scope() as session:
        return [clean(dict(row)) for row in (await session.execute(stmt)).mappings().all()]


async def insert_item(payload: dict[str, Any]) -> None:
    async with session_scope() as session:
        # PantryItem also carries read-time match/status fields; only persist
        # columns belonging to the pantry table.
        values = {column.name: payload[column.name] for column in pantry_items.columns if column.name in payload}
        await session.execute(pantry_items.insert().values(**values))


async def delete_item(item_id: str) -> bool:
    async with session_scope() as session:
        result = await session.execute(delete(pantry_items).where(pantry_items.c.id == item_id))
        return result.rowcount > 0


async def all_items() -> list[dict[str, Any]]:
    async with session_scope() as session:
        return [clean(dict(row)) for row in (await session.execute(select(pantry_items))).mappings().all()]
