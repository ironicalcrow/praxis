"""
Database session and engine configuration.
Handles SQLAlchemy engine creation and session management.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from app.core.config import settings

_engine = None
_SessionLocal = None


def _validate_database_url(url: str) -> str:
    if not url:
        raise RuntimeError(
            "DATABASE_URL is not set. Add DATABASE_URL to your .env file."
        )
    if "[YOUR-PASSWORD]" in url or "YOUR-PASSWORD" in url:
        raise RuntimeError(
            "DATABASE_URL contains a placeholder password. "
            "Replace [YOUR-PASSWORD] with the actual Supabase database password."
        )
    return url.strip()


def init_engine() -> any:
    global _engine, _SessionLocal
    if _engine is not None:
        return _engine

    database_url = _validate_database_url(settings.DATABASE_URL)
    _engine = create_engine(
        database_url,
        echo=False,  # Set to True for SQL query debugging
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,
        pool_recycle=3600,
    )
    _SessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=_engine,
        expire_on_commit=False,
    )
    return _engine


def get_engine() -> any:
    return init_engine()


def get_db() -> Session:
    db = get_session()
    try:
        yield db
    finally:
        db.close()


def get_session() -> Session:
    global _SessionLocal
    if _SessionLocal is None:
        init_engine()
    return _SessionLocal()
