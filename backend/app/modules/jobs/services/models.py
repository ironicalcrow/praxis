from datetime import datetime

from sqlalchemy import Column, String, Text, DateTime, Float, ForeignKey, JSON
from sqlalchemy.orm import relationship

from app.core.session import Base
from app.core.utils import generate_uuid


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
