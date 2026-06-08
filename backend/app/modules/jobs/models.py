from datetime import datetime

from sqlalchemy import (
    Column,
    String,
    Text,
    DateTime,
    Boolean,
    JSON,
    ForeignKey,
    Float,
    Integer,
    Table,
)
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector

from app.core.session import Base
from app.core.config import settings
from app.core.utils import generate_uuid


class UserPreference(Base):
    __tablename__ = "user_preferences"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), unique=True, nullable=False)

    job_types = Column(JSON, nullable=True)
    preference_embedding = Column(Vector(768), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


search_query_jobs = Table(
    "search_query_jobs",
    Base.metadata,
    Column("search_query_id", String, ForeignKey("search_queries.id", ondelete="CASCADE"), primary_key=True),
    Column("job_id", String, ForeignKey("jobs.id", ondelete="CASCADE"), primary_key=True),
)


class SearchQuery(Base):
    __tablename__ = "search_queries"

    id = Column(String, primary_key=True)
    query = Column(String(255), nullable=False)
    location = Column(String(255), nullable=True)
    remote_jobs_only = Column(Boolean, nullable=True)

    last_run_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    jobs = relationship("Job", secondary=search_query_jobs, back_populates="search_queries")


class JobQuery(Base):
    __tablename__ = "job_queries"

    id = Column(String, primary_key=True, default=generate_uuid)
    search_query_id = Column(String, ForeignKey("search_queries.id", ondelete="CASCADE"), nullable=True)
    resume_id = Column(String, ForeignKey("resumes.id"), nullable=False)

    query = Column(String(255), nullable=False)
    reason = Column(String(500))
    priority = Column(Integer)
    added_at = Column(DateTime, default=datetime.utcnow)


class Job(Base):
    __tablename__ = "jobs"

    id = Column(String, primary_key=True, default=generate_uuid)

    external_id = Column(String(255), index=True, nullable=True)
    provider_id = Column(String(100), nullable=True)

    title = Column(String(255), nullable=False)
    job_types = Column(JSON, nullable=True)

    company_name = Column(String(255), nullable=False)
    company_website = Column(Text, nullable=True)
    publisher = Column(String(255), nullable=True)

    location = Column(String(255), nullable=True)
    is_remote = Column(Boolean, nullable=True)

    posted_at = Column(DateTime, nullable=True)
    deadline = Column(DateTime, nullable=True)

    salary = Column(String(255), nullable=True)
    experience_level = Column(String(255), nullable=True)

    apply_urls = Column(JSON, nullable=True)

    description = Column(Text, nullable=True)
    llm_summary = Column(Text, nullable=True)

    skills_and_technologies = Column(JSON, nullable=True)
    responsibilities = Column(JSON, nullable=True)
    qualifications = Column(JSON, nullable=True)
    benefits = Column(JSON, nullable=True)

    job_metadata = Column(JSON, nullable=True)

    embedding = Column(Vector(settings.EMBEDDING_DIMENSIONS), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    applications = relationship("Application", back_populates="job")
    search_queries = relationship("SearchQuery", secondary=search_query_jobs, back_populates="jobs")
    fit_scores = relationship(
        "JobFitScore",
        back_populates="job",
        cascade="all, delete-orphan",
    )


class JobFitScore(Base):
    __tablename__ = "job_fit_scores"

    id = Column(String, primary_key=True, default=generate_uuid)

    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    job_id = Column(String, ForeignKey("jobs.id"), nullable=False)

    fit_score = Column(Float, nullable=False)
    summary = Column(Text, nullable=True)

    matched_skills = Column(JSON, nullable=True)
    missing_skills = Column(JSON, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    job = relationship("Job", back_populates="fit_scores")
