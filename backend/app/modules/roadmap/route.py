from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.session import get_db
from app.modules.auth.dependency import get_current_user
from app.modules.roadmap import db_service as roadmap_db
from app.modules.roadmap import service as roadmap_service
from app.modules.roadmap.schemas import (
    RoadmapOut,
    RoadmapDetailOut,
    ManualRoadmapCreate,
    GenerateFromConversationRequest,
    GenerateFromJobRequest,
)

router = APIRouter()


@router.post("/from-conversation", status_code=201)
async def generate_from_conversation(
    body: GenerateFromConversationRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Generate a structured roadmap from a coaching conversation.

    Flow:
      conversation transcript → LLM → roadmap (phases + milestones)
      → Returns roadmap + suggested_goals list for user review
      → User confirms goals via POST /goals/from-roadmap/{roadmap_id}
    """
    try:
        roadmap = await roadmap_service.generate_from_conversation(
            body.conversation_id, str(current_user.id), db
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Roadmap generation failed: {str(e)}")

    return roadmap_service.build_roadmap_insight_preview(roadmap)


@router.post("/from-job", status_code=201)
async def generate_from_job(
    body: GenerateFromJobRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Generate a gap-analysis roadmap from a job listing.

    Compares the user's CV skills against the job requirements and produces
    a targeted upskilling plan. Returns roadmap + suggested_goals for review.
    """
    try:
        roadmap = await roadmap_service.generate_from_job(
            body.job_id, str(current_user.id), db
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Roadmap generation failed: {str(e)}")

    return roadmap_service.build_roadmap_insight_preview(roadmap)


@router.post("/manual", response_model=RoadmapOut, status_code=201)
def create_manual_roadmap(
    body: ManualRoadmapCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Create a blank roadmap manually. Phases and milestones can be added later."""
    roadmap = roadmap_db.create_roadmap(
        db=db,
        user_id=str(current_user.id),
        title=body.title,
        description=body.description,
        source_type="manual",
        source_id=None,
        phases_data=[],
    )
    return roadmap


@router.get("", response_model=list[RoadmapOut])
def list_roadmaps(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """List all roadmaps for the current user, newest first."""
    return roadmap_db.get_roadmaps(db, str(current_user.id))


@router.get("/{roadmap_id}", response_model=RoadmapDetailOut)
def get_roadmap(
    roadmap_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get a full roadmap with all phases and milestones."""
    roadmap = roadmap_db.get_roadmap(db, roadmap_id, str(current_user.id))
    if not roadmap:
        raise HTTPException(status_code=404, detail="Roadmap not found")
    return roadmap


@router.delete("/{roadmap_id}", status_code=204)
def delete_roadmap(
    roadmap_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    deleted = roadmap_db.delete_roadmap(db, roadmap_id, str(current_user.id))
    if not deleted:
        raise HTTPException(status_code=404, detail="Roadmap not found")
