"""SQLAlchemy async engine, session factory and FastAPI dependency."""

from pathlib import Path
from typing import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncConnection,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

class Base(DeclarativeBase):
    """Declarative base for all ORM models."""

Path("data").mkdir(parents=True, exist_ok=True)

engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    connect_args={"check_same_thread": False},
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency: one session per request, auto-commit on success."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

async def create_tables() -> None:
    """Create all tables and apply lightweight SQLite compatibility migrations."""
    import app.database.models

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await _ensure_sqlite_compatibility(conn)


async def _ensure_sqlite_compatibility(conn: AsyncConnection) -> None:
    """Ensure old SQLite DB files are compatible with current ORM models.

    `create_all()` does not alter existing tables, so older files can miss
    newly introduced columns like `contacts.manual_mode`.
    """
    if not engine.url.drivername.startswith("sqlite"):
        return

    pragma_result = await conn.execute(text("PRAGMA table_info(contacts)"))
    columns = {row[1] for row in pragma_result.fetchall()}
    if "manual_mode" in columns:
        return

    await conn.execute(
        text(
            "ALTER TABLE contacts "
            "ADD COLUMN manual_mode BOOLEAN NOT NULL DEFAULT 0"
        )
    )
