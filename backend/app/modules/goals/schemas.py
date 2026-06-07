from datetime import datetime, date
from typing import Optional, List

from pydantic import BaseModel


class GoalCreate(BaseModel):
    title: str
    description: Optional[str] = None
    target_date: Optional[date] = None


class GoalUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None      # not_started | in_progress | completed | paused
    target_date: Optional[date] = None


class GoalOut(BaseModel):
    id: str
    user_id: str
    title: str
    description: Optional[str] = None
    status: str
    source_type: str
    roadmap_id: Optional[str] = None
    milestone_id: Optional[str] = None
    target_date: Optional[date] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class BulkGoalConfirm(BaseModel):
    """
    Optional filter when promoting roadmap milestones to Goals.
    Omit (or send an empty body) to auto-create goals for ALL milestones.
    """
    milestone_ids: Optional[List[str]] = None
