"""
One-shot script: drop all tables + flush Redis, then recreate tables from current models.
Run from the backend directory: python reset_db.py
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from app.core.config import settings
from sqlalchemy import text
from app.core.session import Base, engine

# Import every model so SQLAlchemy mapper knows all tables
import app.models  # noqa: F401


def reset_database():
    print("Dropping orphan tables not in current models...")
    with engine.connect() as conn:
        conn.execute(text("DROP TABLE IF EXISTS job_fit_scores CASCADE"))
        conn.commit()
    print("Dropping all tables...")
    Base.metadata.drop_all(bind=engine)
    print("Recreating tables from current models...")
    Base.metadata.create_all(bind=engine)
    print("Database reset complete.")


async def flush_redis():
    import redis.asyncio as aioredis
    print("Flushing Redis...")
    r = aioredis.from_url(settings.REDIS_URL)
    await r.flushall()
    await r.aclose()
    print("Redis flushed.")


if __name__ == "__main__":
    reset_database()
    asyncio.run(flush_redis())
    print("\nDone. Fresh DB and Redis ready.")
