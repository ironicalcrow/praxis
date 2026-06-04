from sqlalchemy import Column, String, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from app.models import Base


class JobQuery(Base):
    __tablename__ = "job_queries"
    
    id = Column(UUID(as_uuid=True), primary_key=True)
    resume_id = Column(UUID(as_uuid=True), ForeignKey("resumes.id"), nullable=False)
    query = Column(String(255), nullable=False)
    reason = Column(String(500))
    priority = Column(Integer)
