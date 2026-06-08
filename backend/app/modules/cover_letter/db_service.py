from typing import Optional

from sqlalchemy.orm import Session

from app.modules.cover_letter.models import CoverLetter


def get_or_create_cover_letter(
    db: Session, user_id: str, job_id: str
) -> tuple[CoverLetter, bool]:
    """Return (existing_draft, False) or (new_empty_draft, True)."""
    existing = (
        db.query(CoverLetter)
        .filter(CoverLetter.user_id == user_id, CoverLetter.job_id == job_id)
        .first()
    )
    if existing:
        return existing, False
    draft = CoverLetter(user_id=user_id, job_id=job_id, content="", tone="professional")
    db.add(draft)
    db.commit()
    db.refresh(draft)
    return draft, True


def save_cover_letter(
    db: Session, user_id: str, job_id: str, content: str, tone: str = "professional"
) -> CoverLetter:
    draft, _ = get_or_create_cover_letter(db, user_id, job_id)
    draft.content = content
    draft.tone = tone
    db.commit()
    db.refresh(draft)
    return draft


def get_cover_letters(db: Session, user_id: str) -> list[CoverLetter]:
    return (
        db.query(CoverLetter)
        .filter(CoverLetter.user_id == user_id)
        .order_by(CoverLetter.updated_at.desc())
        .all()
    )


def get_cover_letter(db: Session, cover_letter_id: str, user_id: str) -> Optional[CoverLetter]:
    return (
        db.query(CoverLetter)
        .filter(CoverLetter.id == cover_letter_id, CoverLetter.user_id == user_id)
        .first()
    )


def update_cover_letter(db: Session, cover_letter_id: str, user_id: str, content: str) -> Optional[CoverLetter]:
    draft = get_cover_letter(db, cover_letter_id, user_id)
    if not draft:
        return None
    draft.content = content
    db.commit()
    db.refresh(draft)
    return draft


def delete_cover_letter(db: Session, cover_letter_id: str, user_id: str) -> bool:
    draft = get_cover_letter(db, cover_letter_id, user_id)
    if not draft:
        return False
    db.delete(draft)
    db.commit()
    return True
