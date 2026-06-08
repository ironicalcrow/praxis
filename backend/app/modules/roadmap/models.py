from datetime import datetime

from sqlalchemy import Column, String, Text, DateTime, Integer, ForeignKey
from sqlalchemy.orm import relationship

from app.core.session import Base
from app.core.utils import generate_uuid


class Roadmap(Base):
    __tablename__ = "roadmaps"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # How this roadmap was created: 'chat' | 'job' | 'manual'
    source_type = Column(String(20), nullable=False)
    # conversation_id or job_id — nullable for manual roadmaps
    source_id = Column(String, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    phases = relationship(
        "RoadmapPhase",
        back_populates="roadmap",
        cascade="all, delete-orphan",
        order_by="RoadmapPhase.order_index",
    )
    goals = relationship("Goal", back_populates="roadmap")


class RoadmapPhase(Base):
    """An ordered phase within a roadmap (e.g. 'Foundation Skills')."""
    __tablename__ = "roadmap_phases"

    id = Column(String, primary_key=True, default=generate_uuid)
    roadmap_id = Column(
        String, ForeignKey("roadmaps.id", ondelete="CASCADE"), nullable=False
    )

    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    order_index = Column(Integer, nullable=False, default=0)
    duration_weeks = Column(Integer, nullable=True)

    roadmap = relationship("Roadmap", back_populates="phases")
    milestones = relationship(
        "RoadmapMilestone",
        back_populates="phase",
        cascade="all, delete-orphan",
        order_by="RoadmapMilestone.order_index",
    )


class RoadmapMilestone(Base):
    """A concrete, actionable milestone within a phase."""
    __tablename__ = "roadmap_milestones"

    id = Column(String, primary_key=True, default=generate_uuid)
    phase_id = Column(
        String, ForeignKey("roadmap_phases.id", ondelete="CASCADE"), nullable=False
    )

    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    resource_url = Column(Text, nullable=True)
    order_index = Column(Integer, nullable=False, default=0)
    estimated_days = Column(Integer, nullable=True)
    suggested_target_days = Column(Integer, nullable=True)
    key_skill = Column(String, nullable=True)

    phase = relationship("RoadmapPhase", back_populates="milestones")
    goals = relationship("Goal", back_populates="milestone")
