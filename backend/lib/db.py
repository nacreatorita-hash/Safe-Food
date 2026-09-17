"""Shared async SQLAlchemy handle for Supabase Postgres."""

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

from dotenv import load_dotenv
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

load_dotenv(Path(__file__).parent.parent / ".env")

logger = logging.getLogger(__name__)


def _database_url() -> str:
    value = os.environ.get("DATABASE_URL", "").strip()
    if not value:
        raise RuntimeError("DATABASE_URL non configurato: inserire la connection string Supabase in backend/.env")
    if value.startswith("postgres://"):
        return "postgresql+asyncpg://" + value.removeprefix("postgres://")
    if value.startswith("postgresql://"):
        return "postgresql+asyncpg://" + value.removeprefix("postgresql://")
    if not value.startswith("postgresql+asyncpg://"):
        raise RuntimeError("DATABASE_URL deve usare postgres://, postgresql:// o postgresql+asyncpg://")
    return value


engine = create_async_engine(
    _database_url(),
    pool_pre_ping=True,
    pool_recycle=1800,
    # Supabase transaction pooler (port 6543) is PgBouncer-backed; prepared
    # statement caching must be disabled for connections that can move between
    # backend sessions.
    connect_args={
        "timeout": float(os.environ.get("DB_CONNECT_TIMEOUT_SECONDS", "5")),
        "statement_cache_size": 0,
    },
)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


@asynccontextmanager
async def session_scope() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def check_database() -> None:
    async with engine.connect() as connection:
        await connection.execute(text("select 1"))


async def ensure_indexes() -> None:
    """Schema/indexes are managed by versioned SQL migrations in Supabase."""
    logger.debug("Supabase schema is managed by backend/migrations")


async def close() -> None:
    await engine.dispose()
