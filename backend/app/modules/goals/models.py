from datetime import datetime

from sqlalchemy import Column, String, Text, DateTime, Date, ForeignKey
from sqlalchemy.orm import relationship

from app.core.session import Base
from app.core.utils import generate_uuid


class Goal(Base):
    __tablename__ = "goals"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # not_started | in_progress | completed | paused
    status = Column(String(20), nullable=False, default="not_started")

    # roadmap | manual
    source_type = Column(String(20), nullable=False, default="manual")

    # nullable — only set when source_type == 'roadmap'
    roadmap_id = Column(
        String, ForeignKey("roadmaps.id", ondelete="SET NULL"), nullable=True
    )
    milestone_id = Column(
        String, ForeignKey("roadmap_milestones.id", ondelete="SET NULL"), nullable=True
    )

    target_date = Column(Date, nullable=True)
    key_skill = Column(String, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    roadmap = relationship("Roadmap", back_populates="goals")
    milestone = relationship("RoadmapMilestone", back_populates="goals")
