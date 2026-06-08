from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.session import get_db
from app.modules.auth.dependency import get_current_user
from app.modules.cover_letter import db_service as cl_db
from app.modules.cover_letter import service as cl_service
from app.modules.cover_letter.schemas import (
    CoverLetterGenerate,
    CoverLetterUpdate,
    CoverLetterOut,
)

router = APIRouter()


@router.post("/generate", response_model=CoverLetterOut)
async def generate_cover_letter(
    body: CoverLetterGenerate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """One-click cover letter generation for a job. Saves and returns the draft."""
    try:
        draft = await cl_service.generate_cover_letter(
            user_id=str(current_user.id),
            job_id=body.job_id,
            tone=body.tone,
            db=db,
        )
        try:
            from app.modules.notifications.service import create_and_publish as notify
            import asyncio
            asyncio.create_task(notify(
                user_id=str(current_user.id),
                type="cover_letter_ready",
                title="Cover letter ready",
                message="Your cover letter draft has been generated.",
                data={"cover_letter_id": str(draft.id), "job_id": body.job_id},
            ))
        except Exception:
            pass
        return draft
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cover letter generation failed: {str(e)}")


@router.get("/", response_model=list[CoverLetterOut])
def list_cover_letters(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return cl_db.get_cover_letters(db, str(current_user.id))


@router.get("/{cover_letter_id}", response_model=CoverLetterOut)
def get_cover_letter(
    cover_letter_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    draft = cl_db.get_cover_letter(db, cover_letter_id, str(current_user.id))
    if not draft:
        raise HTTPException(status_code=404, detail="Cover letter not found")
    return draft


@router.patch("/{cover_letter_id}", response_model=CoverLetterOut)
def update_cover_letter(
    cover_letter_id: str,
    body: CoverLetterUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    draft = cl_db.update_cover_letter(db, cover_letter_id, str(current_user.id), body.content)
    if not draft:
        raise HTTPException(status_code=404, detail="Cover letter not found")
    return draft


@router.delete("/{cover_letter_id}", status_code=204)
def delete_cover_letter(
    cover_letter_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    deleted = cl_db.delete_cover_letter(db, cover_letter_id, str(current_user.id))
    if not deleted:
        raise HTTPException(status_code=404, detail="Cover letter not found")
