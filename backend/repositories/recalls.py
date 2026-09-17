from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import Text, and_, cast, desc, func, not_, or_, select, update

from lib.db import session_scope
from models.tables import recalls

MAX_SEARCH_LENGTH = 100


def clean(doc: dict[str, Any]) -> dict[str, Any]:
    return dict(doc)


def search_pattern(value: str | None) -> str | None:
    if not value:
        return None
    value = value.strip()
    return value[:MAX_SEARCH_LENGTH] or None


def _search_clauses(value: str) -> list[Any]:
    lowered = value.lower()
    return [
        func.lower(recalls.c.product_name).contains(lowered, autoescape=True),
        func.lower(recalls.c.brand).contains(lowered, autoescape=True),
        func.lower(recalls.c.title).contains(lowered, autoescape=True),
        func.lower(recalls.c.ean).contains(lowered, autoescape=True),
        func.lower(recalls.c.producer).contains(lowered, autoescape=True),
        func.lower(cast(recalls.c.lots, Text)).contains(lowered, autoescape=True),
    ]


async def list_recalls(query: dict[str, Any], sort: str, limit: int) -> list[dict[str, Any]]:
    stmt = select(recalls)
    if query.get("q"):
        stmt = stmt.where(or_(*_search_clauses(str(query["q"]))))
    for key in ("risk_type", "brand", "category", "is_seafood"):
        if key in query:
            stmt = stmt.where(getattr(recalls.c, key) == query[key])
    if sort == "name":
        stmt = stmt.order_by(recalls.c.product_name.asc())
    elif sort == "oldest":
        stmt = stmt.order_by(recalls.c.published_at.asc())
    else:
        stmt = stmt.order_by(recalls.c.published_at.desc())
    stmt = stmt.limit(limit)
    async with session_scope() as session:
        result = await session.execute(stmt)
        return [clean(dict(row)) for row in result.mappings().all()]


async def recall_stats() -> dict[str, int]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=30)
    stmt = select(
        func.count(recalls.c.id).label("total"),
        func.count(recalls.c.id).filter(recalls.c.published_at >= cutoff).label("last_30_days"),
        func.count(recalls.c.id).filter(recalls.c.risk_type == "microbiologico").label("microbiologico"),
        func.count(recalls.c.id).filter(recalls.c.risk_type == "allergeni").label("allergeni"),
        func.count(recalls.c.id).filter(recalls.c.risk_type == "chimico").label("chimico"),
        func.count(recalls.c.id).filter(recalls.c.risk_type == "fisico").label("fisico"),
        func.count(recalls.c.id).filter(recalls.c.is_seafood.is_(True)).label("seafood"),
    )
    async with session_scope() as session:
        row = (await session.execute(stmt)).mappings().one()
        return {key: int(row[key] or 0) for key in ("total", "last_30_days", "microbiologico", "allergeni", "chimico", "fisico", "seafood")}


async def list_brands() -> list[str]:
    stmt = select(recalls.c.brand).where(recalls.c.brand.is_not(None)).distinct().order_by(recalls.c.brand.asc())
    async with session_scope() as session:
        return [str(row[0]) for row in (await session.execute(stmt)).all() if row[0]]


async def get_recall(recall_id: str) -> dict[str, Any] | None:
    async with session_scope() as session:
        row = (await session.execute(select(recalls).where(recalls.c.id == recall_id))).mappings().first()
        return clean(dict(row)) if row else None


async def find_by_source(source: str, source_id: str) -> dict[str, Any] | None:
    async with session_scope() as session:
        row = (await session.execute(select(recalls).where(recalls.c.source == source, recalls.c.source_id == source_id))).mappings().first()
        return clean(dict(row)) if row else None


async def list_source_ids(source: str) -> set[str]:
    async with session_scope() as session:
        rows = await session.execute(select(recalls.c.source_id).where(recalls.c.source == source))
        return {str(row[0]) for row in rows.all()}


async def list_recent_source_records(source: str, since: datetime, limit: int) -> list[dict[str, Any]]:
    """Return a small, recent slice for cheap official-page rechecks."""
    stmt = (
        select(recalls)
        .where(recalls.c.source == source, recalls.c.published_at >= since, recalls.c.source_url.is_not(None))
        .order_by(desc(recalls.c.published_at))
        .limit(limit)
    )
    async with session_scope() as session:
        return [clean(dict(row)) for row in (await session.execute(stmt)).mappings().all()]


async def update_by_source(source: str, source_id: str, values: dict[str, Any]) -> bool:
    """Apply a bounded official-source correction to an existing recall."""
    async with session_scope() as session:
        result = await session.execute(
            update(recalls)
            .where(recalls.c.source == source, recalls.c.source_id == source_id)
            .values(**values)
        )
        return bool(result.rowcount)


async def list_source_ids_needing_enrichment(source: str, limit: int) -> set[str]:
    """Return records whose available official document has not been checked.

    A page without a linked PDF is marked once as ``_document_checked`` by the
    ingestion service. This keeps the scheduler from retrying permanently
    document-less archive entries on every run while still allowing records
    with a PDF to receive OCR/image enrichment.
    """
    async with session_scope() as session:
        rows = await session.execute(
            select(recalls.c.source_id)
            .where(
                recalls.c.source == source,
                or_(
                    and_(recalls.c.pdf_url.is_(None), not_(recalls.c.official_fields.has_key("_document_checked"))),
                    and_(recalls.c.pdf_url.is_not(None), not_(recalls.c.official_fields.has_key("_ocr_checked"))),
                    and_(recalls.c.pdf_url.is_not(None), not_(recalls.c.official_fields.has_key("_origin_checked"))),
                ),
            )
            .order_by(recalls.c.published_at.desc())
            .limit(limit)
        )
        return {str(row[0]) for row in rows.all()}


async def candidate_recalls(item: dict[str, Any]) -> list[dict[str, Any]]:
    conditions = []
    if item.get("ean"):
        conditions.append(recalls.c.ean == item["ean"])
    if item.get("brand"):
        conditions.append(recalls.c.brand == item["brand"])
    if item.get("name"):
        conditions.extend(_search_clauses(str(item["name"])))
    if not conditions:
        return []
    stmt = select(recalls).where(or_(*conditions)).order_by(recalls.c.published_at.desc()).limit(200)
    async with session_scope() as session:
        return [clean(dict(row)) for row in (await session.execute(stmt)).mappings().all()]


async def count_for_source(source: str) -> int:
    async with session_scope() as session:
        value = await session.scalar(select(func.count(recalls.c.id)).where(recalls.c.source == source))
        return int(value or 0)
