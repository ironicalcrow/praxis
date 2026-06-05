import enum
import uuid
from datetime import datetime

from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Boolean, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID

from app.core.session import Base


def generate_uuid():
    return str(uuid.uuid4())


class ApplicationStatus(str, enum.Enum):
    SAVED = "saved"
    APPLIED = "applied"
    INTERVIEWING = "interviewing"
    OFFER = "offer"
    REJECTED = "rejected"


class Application(Base):
    __tablename__ = "applications"

    id = Column(String, primary_key=True, default=generate_uuid)

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    job_id = Column(String, ForeignKey("jobs.id"), nullable=True)

    status = Column(
        SQLEnum(ApplicationStatus),
        nullable=False,
        default=ApplicationStatus.SAVED,
        index=True,
    )

    job_title = Column(String(255), nullable=False)
    company = Column(String(255), nullable=False)
    location = Column(String(255), nullable=True)
    apply_url = Column(Text, nullable=True)
    source = Column(String(100), nullable=True)
    salary = Column(String(255), nullable=True)

    applied_at = Column(DateTime, nullable=True)
    last_status_changed_at = Column(DateTime, default=datetime.utcnow)

    is_archived = Column(Boolean, default=False, index=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="applications")
    job = relationship("Job", back_populates="applications")

    status_history = relationship(
        "ApplicationStatusHistory",
        back_populates="application",
        cascade="all, delete-orphan",
        order_by="ApplicationStatusHistory.changed_at.desc()",
    )

    notes = relationship(
        "ApplicationNote",
        back_populates="application",
        cascade="all, delete-orphan",
        order_by="ApplicationNote.created_at.desc()",
    )


class ApplicationStatusHistory(Base):
    __tablename__ = "application_status_history"

    id = Column(String, primary_key=True, default=generate_uuid)

    application_id = Column(String, ForeignKey("applications.id"), nullable=False)

    old_status = Column(SQLEnum(ApplicationStatus), nullable=True)
    new_status = Column(SQLEnum(ApplicationStatus), nullable=False)

    changed_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    reason = Column(Text, nullable=True)

    changed_at = Column(DateTime, default=datetime.utcnow)

    application = relationship("Application", back_populates="status_history")


class ApplicationNote(Base):
    __tablename__ = "application_notes"

    id = Column(String, primary_key=True, default=generate_uuid)

    application_id = Column(String, ForeignKey("applications.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    content = Column(Text, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    application = relationship("Application", back_populates="notes")