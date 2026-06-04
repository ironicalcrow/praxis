"""
Database session and engine configuration.
Handles SQLAlchemy engine creation and session management.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from app.core.config import settings

# Create SQLAlchemy engine with PostgreSQL
engine = create_engine(
    settings.DATABASE_URL,
    echo=False,  # Set to True for SQL query debugging
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,  # Test connections before using them
    pool_recycle=3600,  # Recycle connections every hour
)

# Create session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False,
)


def get_db() -> Session:
    """
    Dependency function for FastAPI to provide database sessions.
    Use in routes with: Depends(get_db)
    
    Example:
        @app.get("/users")
        def get_users(db: Session = Depends(get_db)):
            return db.query(User).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_session() -> Session:
    """
    Get a new database session.
    Use this for non-FastAPI code (services, utilities, etc.)
    
    Example:
        db = get_session()
        try:
            user = db.query(User).first()
        finally:
            db.close()
    """
    return SessionLocal()
