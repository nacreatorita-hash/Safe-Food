from typing import Any

from sqlalchemy import update, select, func

from lib.db import session_scope
from models.tables import notifications


def clean(doc: dict[str, Any]) -> dict[str, Any]:
    return dict(doc)


async def list_notifications() -> list[dict[str, Any]]:
    stmt = select(notifications).order_by(notifications.c.created_at.desc()).limit(200)
    async with session_scope() as session:
        return [clean(dict(row)) for row in (await session.execute(stmt)).mappings().all()]


async def mark_read(note_id: str) -> dict[str, Any] | None:
    async with session_scope() as session:
        await session.execute(update(notifications).where(notifications.c.id == note_id).values(read=True))
        row = (await session.execute(select(notifications).where(notifications.c.id == note_id))).mappings().first()
        return clean(dict(row)) if row else None


async def mark_all_read() -> int:
    async with session_scope() as session:
        result = await session.execute(update(notifications).where(notifications.c.read.is_(False)).values(read=True))
        return int(result.rowcount or 0)


async def insert(payload: dict[str, Any]) -> None:
    async with session_scope() as session:
        await session.execute(notifications.insert().values(**payload))


async def count() -> int:
    async with session_scope() as session:
        value = await session.scalar(select(func.count(notifications.c.id)))
        return int(value or 0)
