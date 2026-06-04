"""
Database session and engine configuration.
Handles SQLAlchemy engine creation and session management.
"""

import socket

from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
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
    database_url = url.strip()
    try:
        parsed_url = make_url(database_url)
    except Exception as exc:
        raise RuntimeError("DATABASE_URL is not a valid SQLAlchemy database URL.") from exc

    if not parsed_url.host:
        raise RuntimeError("DATABASE_URL must include a database host.")

    try:
        socket.getaddrinfo(parsed_url.host, parsed_url.port)
    except socket.gaierror as exc:
        hint = ""
        if parsed_url.host.startswith("db.") and parsed_url.host.endswith(".supabase.co"):
            hint = (
                " Supabase direct database hosts use IPv6 unless the project has the "
                "IPv4 add-on. If your network is IPv4-only, replace DATABASE_URL with "
                "the Session pooler connection string from Supabase Dashboard > Connect."
            )
        raise RuntimeError(
            f"Could not resolve database host '{parsed_url.host}'.{hint}"
        ) from exc

    return database_url


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
