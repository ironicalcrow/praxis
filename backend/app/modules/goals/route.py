from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.session import get_db
from app.modules.auth.dependency import get_current_user
from app.modules.goals import db_service as goals_db
from app.modules.goals.schemas import GoalCreate, GoalUpdate, GoalOut, BulkGoalConfirm
from app.modules.roadmap import db_service as roadmap_db

router = APIRouter()

_VALID_STATUSES = {"not_started", "in_progress", "completed", "paused"}


@router.post("", response_model=GoalOut, status_code=201)
def create_goal(
    body: GoalCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Create a manual goal not tied to any roadmap."""
    return goals_db.create_goal(
        db=db,
        user_id=str(current_user.id),
        title=body.title,
        description=body.description,
        target_date=body.target_date,
        source_type="manual",
    )


@router.post("/from-roadmap/{roadmap_id}", response_model=list[GoalOut], status_code=201)
def create_goals_from_roadmap(
    roadmap_id: UUID,
    body: Optional[BulkGoalConfirm] = Body(default=None),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    
    roadmap_id = str(roadmap_id)
    user_id = str(current_user.id)
    print(f"[goals/from-roadmap] roadmap_id={roadmap_id!r}  user_id={user_id!r}")

    roadmap = roadmap_db.get_roadmap(db, roadmap_id, user_id)
    print(f"[goals/from-roadmap] roadmap lookup → {roadmap}")
    if not roadmap:
        raise HTTPException(status_code=404, detail="Roadmap not found")

    milestone_ids = body.milestone_ids if (body and body.milestone_ids) else None

    goals = goals_db.create_goals_from_milestones(
        db=db,
        user_id=user_id,
        roadmap_id=roadmap_id,
        milestone_ids=milestone_ids,
    )
    print(f"[goals/from-roadmap] goals created → {len(goals)}")
    return goals


@router.get("", response_model=list[GoalOut])
def list_goals(
    status: Optional[str] = Query(
        default=None,
        description="Filter by status: not_started | in_progress | completed | paused",
    ),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if status and status not in _VALID_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Must be one of: {', '.join(_VALID_STATUSES)}",
        )
    return goals_db.get_goals(db, str(current_user.id), status)


@router.get("/{goal_id}", response_model=GoalOut)
def get_goal(
    goal_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    goal_id = str(goal_id)
    goal = goals_db.get_goal(db, goal_id, str(current_user.id))
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    return goal


@router.patch("/{goal_id}", response_model=GoalOut)
def update_goal(
    goal_id: UUID,
    body: GoalUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    goal_id = str(goal_id)
    data = body.model_dump(exclude_none=True)

    if "status" in data and data["status"] not in _VALID_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Must be one of: {', '.join(_VALID_STATUSES)}",
        )

    goal = goals_db.update_goal(db, goal_id, str(current_user.id), data)
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    return goal


@router.delete("/{goal_id}", status_code=204)
def delete_goal(
    goal_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    goal_id = str(goal_id)
    deleted = goals_db.delete_goal(db, goal_id, str(current_user.id))
    if not deleted:
        raise HTTPException(status_code=404, detail="Goal not found")
