from typing import Any

from sqlalchemy import select

from lib.db import session_scope
from models.tables import status_checks


async def insert_status(payload: dict[str, Any]) -> None:
    async with session_scope() as session:
        await session.execute(status_checks.insert().values(**payload))


async def list_status() -> list[dict[str, Any]]:
    stmt = select(status_checks).order_by(status_checks.c.timestamp.desc()).limit(1000)
    async with session_scope() as session:
        return [dict(row) for row in (await session.execute(stmt)).mappings().all()]
