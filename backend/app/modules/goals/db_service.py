from datetime import date, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from app.modules.goals.models import Goal
from app.modules.roadmap.db_service import get_all_milestones_for_roadmap

VALID_STATUSES = {"not_started", "in_progress", "completed", "paused"}


def create_goal(
    db: Session,
    user_id: str,
    title: str,
    description: Optional[str] = None,
    target_date=None,
    source_type: str = "manual",
    roadmap_id: Optional[str] = None,
    milestone_id: Optional[str] = None,
) -> Goal:
    goal = Goal(
        user_id=user_id,
        title=title,
        description=description,
        target_date=target_date,
        source_type=source_type,
        roadmap_id=roadmap_id,
        milestone_id=milestone_id,
        status="not_started",
    )
    db.add(goal)
    db.commit()
    db.refresh(goal)
    return goal


def create_goals_from_milestones(
    db: Session,
    user_id: str,
    roadmap_id: str,
    milestone_ids: Optional[list[str]] = None,
) -> list[Goal]:

    all_milestones = get_all_milestones_for_roadmap(db, roadmap_id)
    print(f"[create_goals_from_milestones] roadmap_id={roadmap_id!r}  milestones found={len(all_milestones)}")
    for m in all_milestones:
        print(f"  milestone id={m.id!r}  title={m.title!r}")

    if milestone_ids:  # None or [] both mean "create for all milestones"
        requested_set = set(milestone_ids)
        milestones_to_use = [m for m in all_milestones if m.id in requested_set]
    else:
        milestones_to_use = all_milestones

    print(f"[create_goals_from_milestones] milestones_to_use={len(milestones_to_use)}")

    # Build a day-offset map for every milestone so sequential goals get
    # cumulative deadlines (milestone 2 starts after milestone 1 ends, etc.).
    offset_map: dict[str, int] = {}
    running_days = 0
    for m in milestones_to_use:
        days = m.suggested_target_days or m.estimated_days or 0
        running_days += days
        offset_map[m.id] = running_days

    today = date.today()
    goals = []
    for milestone in milestones_to_use:
        total_days = offset_map[milestone.id]
        target = today + timedelta(days=total_days) if total_days else None

        goal = Goal(
            user_id=user_id,
            title=milestone.title,
            description=milestone.description,
            source_type="roadmap",
            roadmap_id=roadmap_id,
            milestone_id=milestone.id,
            status="not_started",
            target_date=target,
            key_skill=milestone.key_skill,
        )
        db.add(goal)
        goals.append(goal)

    db.commit()
    for g in goals:
        db.refresh(g)

    return goals


def get_goals(
    db: Session, user_id: str, status: Optional[str] = None
) -> list[Goal]:
    q = db.query(Goal).filter(Goal.user_id == user_id)
    if status:
        q = q.filter(Goal.status == status)
    return q.order_by(Goal.created_at.desc()).all()


def get_goal(db: Session, goal_id: str, user_id: str) -> Optional[Goal]:
    return (
        db.query(Goal)
        .filter(Goal.id == goal_id, Goal.user_id == user_id)
        .first()
    )


def update_goal(db: Session, goal_id: str, user_id: str, data: dict) -> Optional[Goal]:
    goal = get_goal(db, goal_id, user_id)
    if not goal:
        return None
    for key, value in data.items():
        if hasattr(goal, key):
            setattr(goal, key, value)
    db.commit()
    db.refresh(goal)
    return goal


def delete_goal(db: Session, goal_id: str, user_id: str) -> bool:
    goal = get_goal(db, goal_id, user_id)
    if not goal:
        return False
    db.delete(goal)
    db.commit()
    return True
