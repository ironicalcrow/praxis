"""Builders for the goals / roadmap / notifications suites."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class FakeUser:
    """
    Stands in for the Supabase user object returned by `get_current_user`.
    Routes only ever read `.id` and `.email`.
    """

    id: str
    email: str = "test@example.com"


def make_roadmap(
    db,
    user_id: str,
    title: str = "Backend Engineer Roadmap",
    description: Optional[str] = "Path to a backend role",
    source_type: str = "manual",
    source_id: Optional[str] = None,
):
    from app.modules.roadmap.models import Roadmap

    roadmap = Roadmap(
        user_id=user_id,
        title=title,
        description=description,
        source_type=source_type,
        source_id=source_id,
    )
    db.add(roadmap)
    db.commit()
    db.refresh(roadmap)
    return roadmap


def make_phase(
    db,
    roadmap_id: str,
    title: str = "Foundation Skills",
    order_index: int = 0,
    duration_weeks: Optional[int] = 4,
):
    from app.modules.roadmap.models import RoadmapPhase

    phase = RoadmapPhase(
        roadmap_id=roadmap_id,
        title=title,
        description=f"{title} description",
        order_index=order_index,
        duration_weeks=duration_weeks,
    )
    db.add(phase)
    db.commit()
    db.refresh(phase)
    return phase


def make_milestone(
    db,
    phase_id: str,
    title: str = "Learn SQL joins",
    order_index: int = 0,
    estimated_days: Optional[int] = 7,
    suggested_target_days: Optional[int] = None,
):
    from app.modules.roadmap.models import RoadmapMilestone

    milestone = RoadmapMilestone(
        phase_id=phase_id,
        title=title,
        description=f"{title} description",
        order_index=order_index,
        estimated_days=estimated_days,
        suggested_target_days=suggested_target_days,
    )
    db.add(milestone)
    db.commit()
    db.refresh(milestone)
    return milestone


def make_roadmap_with_milestones(db, user_id: str, milestone_titles=None):
    """
    A roadmap with one phase and N milestones — the shape
    `POST /api/goals/from-roadmap/{id}` expects.

    Returns (roadmap, phase, [milestones]).
    """
    titles = milestone_titles or ["Learn SQL joins", "Build a REST API", "Ship to prod"]
    roadmap = make_roadmap(db, user_id)
    phase = make_phase(db, roadmap.id)
    milestones = [
        make_milestone(db, phase.id, title=t, order_index=i)
        for i, t in enumerate(titles)
    ]
    return roadmap, phase, milestones


def make_goal(
    db,
    user_id: str,
    title: str = "Finish the SQL course",
    status: str = "not_started",
    source_type: str = "manual",
    roadmap_id: Optional[str] = None,
    milestone_id: Optional[str] = None,
    description: Optional[str] = "A goal description",
    target_date=None,
):
    from app.modules.goals.models import Goal

    goal = Goal(
        user_id=user_id,
        title=title,
        description=description,
        status=status,
        source_type=source_type,
        roadmap_id=roadmap_id,
        milestone_id=milestone_id,
        target_date=target_date,
    )
    db.add(goal)
    db.commit()
    db.refresh(goal)
    return goal


def make_notification(
    db,
    user_id: str,
    type: str = "goal_completed",
    title: str = "Goal completed!",
    message: str = "You completed a goal.",
    data: Optional[dict] = None,
    is_read: bool = False,
    created_at: Optional[datetime] = None,
):
    from app.modules.notifications.models import Notification

    notification = Notification(
        user_id=user_id,
        type=type,
        title=title,
        message=message,
        data=data,
        is_read=is_read,
    )
    if created_at is not None:
        notification.created_at = created_at
    db.add(notification)
    db.commit()
    db.refresh(notification)
    return notification


def notifications_for(db, user_id: str):
    from app.modules.notifications.models import Notification

    return (
        db.query(Notification)
        .filter(Notification.user_id == user_id)
        .order_by(Notification.created_at.desc())
        .all()
    )


def goals_for(db, user_id: str):
    from app.modules.goals.models import Goal

    return db.query(Goal).filter(Goal.user_id == user_id).all()


# UUIDs that are syntactically valid but never seeded — for 404 assertions.
MISSING_UUID = "99999999-9999-4999-8999-999999999999"
