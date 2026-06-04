import uuid
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
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.session import Base


def generate_uuid():
    return str(uuid.uuid4())


class JobQuery(Base):
    __tablename__ = "job_queries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # FIXED:
    # Resume.id is String, so resume_id must also be String.
    resume_id = Column(String, ForeignKey("resumes.id"), nullable=False)

    query = Column(String(255), nullable=False)
    reason = Column(String(500))
    priority = Column(Integer)


class Job(Base):
    __tablename__ = "jobs"

    id = Column(String, primary_key=True, default=generate_uuid)

    external_id = Column(String(255), index=True, nullable=True)
    source = Column(String(100), nullable=True)

    title = Column(String(255), nullable=False)
    company = Column(String(255), nullable=False)

    company_logo = Column(Text, nullable=True)
    company_website = Column(Text, nullable=True)

    publisher = Column(String(255), nullable=True)
    employment_type = Column(String(100), nullable=True)
    employment_types = Column(JSON, nullable=True)

    location = Column(String(255), nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)
    country = Column(String(100), nullable=True)
    is_remote = Column(Boolean, default=False)

    apply_url = Column(Text, nullable=True)
    is_direct_apply = Column(Boolean, default=False)

    description_preview = Column(Text, nullable=True)
    salary = Column(String(255), nullable=True)

    raw_payload = Column(JSON, nullable=True)

    posted_at = Column(DateTime, nullable=True)
    deadline = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    applications = relationship("Application", back_populates="job")
    fit_scores = relationship(
        "JobFitScore",
        back_populates="job",
        cascade="all, delete-orphan",
    )


class JobFitScore(Base):
    __tablename__ = "job_fit_scores"

    id = Column(String, primary_key=True, default=generate_uuid)

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    job_id = Column(String, ForeignKey("jobs.id"), nullable=False)

    fit_score = Column(Float, nullable=False)
    summary = Column(Text, nullable=True)

    matched_skills = Column(JSON, nullable=True)
    missing_skills = Column(JSON, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    job = relationship("Job", back_populates="fit_scores")