from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel

from app.core.utils import UUIDStr


# ── Milestone ──────────────────────────────────────────────────────────────────

class MilestoneOut(BaseModel):
    id: str
    phase_id: str
    title: str
    description: Optional[str] = None
    resource_url: Optional[str] = None
    order_index: int
    estimated_days: Optional[int] = None
    suggested_target_days: Optional[int] = None
    key_skill: Optional[str] = None

    class Config:
        from_attributes = True


# ── Phase ──────────────────────────────────────────────────────────────────────

class PhaseOut(BaseModel):
    id: str
    roadmap_id: str
    title: str
    description: Optional[str] = None
    order_index: int
    duration_weeks: Optional[int] = None
    milestones: List[MilestoneOut] = []

    class Config:
        from_attributes = True


# ── Roadmap ────────────────────────────────────────────────────────────────────

class RoadmapOut(BaseModel):
    id: str
    user_id: UUIDStr
    title: str
    description: Optional[str] = None
    source_type: str
    source_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class RoadmapDetailOut(RoadmapOut):
    """Full roadmap including nested phases and milestones."""
    phases: List[PhaseOut] = []


# ── Request Bodies ─────────────────────────────────────────────────────────────

class GenerateFromConversationRequest(BaseModel):
    conversation_id: str


class GenerateFromJobRequest(BaseModel):
    job_id: str


class ManualRoadmapCreate(BaseModel):
    title: str
    description: Optional[str] = None


# ── Preview Returned After Generation ─────────────────────────────────────────

class SuggestedGoal(BaseModel):
    """One suggested goal derived from a roadmap milestone — presented to user for review."""
    title: str
    description: Optional[str] = None
    milestone_id: str
    phase_title: str


class RoadmapInsightPreview(BaseModel):
    """
    Returned after roadmap generation (from conversation or job).
    The user reviews suggested_goals and confirms which to create
    via POST /goals/from-roadmap/{roadmap_id}.
    """
    roadmap: RoadmapDetailOut
    suggested_goals: List[SuggestedGoal]
