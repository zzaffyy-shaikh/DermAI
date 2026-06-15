"""Database engine, session factory, and initialization (SQLite via SQLAlchemy)."""
from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import get_settings

_settings = get_settings()
_connect_args = {"check_same_thread": False} if _settings.database_url.startswith("sqlite") else {}

engine = create_engine(_settings.database_url, connect_args=_connect_args, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


class Base(DeclarativeBase):
    pass


def get_db() -> Iterator[Session]:
    """FastAPI dependency that yields a request-scoped DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _migrate() -> None:
    """Tiny additive migration for SQLite: add new columns to an existing users table."""
    if not _settings.database_url.startswith("sqlite"):
        return
    with engine.begin() as conn:
        cols = {row[1] for row in conn.exec_driver_sql("PRAGMA table_info(users)").fetchall()}
        if cols and "medical_history" not in cols:
            conn.exec_driver_sql("ALTER TABLE users ADD COLUMN medical_history TEXT")
        if cols and "history_completed" not in cols:
            conn.exec_driver_sql("ALTER TABLE users ADD COLUMN history_completed BOOLEAN DEFAULT 0")
        for col in ("qualification", "graduation", "house_job", "pmdc_number", "license_path"):
            if cols and col not in cols:
                conn.exec_driver_sql(f"ALTER TABLE users ADD COLUMN {col} TEXT")


def init_db() -> None:
    """Create tables and seed the admin account. Called once at startup."""
    from . import models  # noqa: F401 - ensure models are registered on Base
    from .services.auth import ensure_admin

    Base.metadata.create_all(engine)
    _migrate()
    db = SessionLocal()
    try:
        ensure_admin(db)
    finally:
        db.close()
