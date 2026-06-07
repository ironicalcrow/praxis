from typing import Optional

from sqlalchemy.orm import Session

from app.modules.roadmap.models import Roadmap, RoadmapPhase, RoadmapMilestone


def create_roadmap(
    db: Session,
    user_id: str,
    title: str,
    description: Optional[str],
    source_type: str,
    source_id: Optional[str],
    phases_data: list[dict],
) -> Roadmap:
    """
    Persist a complete roadmap tree in one transaction.
    phases_data is the parsed LLM output list (or empty for manual roadmaps).
    """
    roadmap = Roadmap(
        user_id=user_id,
        title=title,
        description=description,
        source_type=source_type,
        source_id=source_id,
    )
    db.add(roadmap)
    db.flush()  # populate roadmap.id before inserting children

    for i, phase_data in enumerate(phases_data):
        phase = RoadmapPhase(
            roadmap_id=roadmap.id,
            title=phase_data["title"],
            description=phase_data.get("description"),
            order_index=phase_data.get("order_index", i),
            duration_weeks=phase_data.get("duration_weeks"),
        )
        db.add(phase)
        db.flush()  # populate phase.id before inserting milestones

        for j, m_data in enumerate(phase_data.get("milestones", [])):
            milestone = RoadmapMilestone(
                phase_id=phase.id,
                title=m_data["title"],
                description=m_data.get("description"),
                resource_url=m_data.get("resource_url"),
                order_index=m_data.get("order_index", j),
                estimated_days=m_data.get("estimated_days"),
                suggested_target_days=m_data.get("suggested_target_days"),
            )
            db.add(milestone)

    db.commit()
    db.refresh(roadmap)
    return roadmap


def get_roadmaps(db: Session, user_id: str) -> list[Roadmap]:
    return (
        db.query(Roadmap)
        .filter(Roadmap.user_id == user_id)
        .order_by(Roadmap.created_at.desc())
        .all()
    )


def get_roadmap(db: Session, roadmap_id: str, user_id: str) -> Optional[Roadmap]:
    return (
        db.query(Roadmap)
        .filter(Roadmap.id == roadmap_id, Roadmap.user_id == user_id)
        .first()
    )


def delete_roadmap(db: Session, roadmap_id: str, user_id: str) -> bool:
    roadmap = get_roadmap(db, roadmap_id, user_id)
    if not roadmap:
        return False
    db.delete(roadmap)
    db.commit()
    return True


def get_all_milestones_for_roadmap(db: Session, roadmap_id: str) -> list[RoadmapMilestone]:
    """Flat list of all milestones across all phases, ordered by phase then milestone index."""
    from app.modules.roadmap.models import RoadmapPhase as _RoadmapPhase
    phase_count = db.query(_RoadmapPhase).filter(_RoadmapPhase.roadmap_id == roadmap_id).count()
    print(f"[get_all_milestones_for_roadmap] roadmap_id={roadmap_id!r}  phases in DB={phase_count}")

    results = (
        db.query(RoadmapMilestone)
        .join(RoadmapPhase, RoadmapMilestone.phase_id == RoadmapPhase.id)
        .filter(RoadmapPhase.roadmap_id == roadmap_id)
        .order_by(RoadmapPhase.order_index, RoadmapMilestone.order_index)
        .all()
    )
    print(f"[get_all_milestones_for_roadmap] milestone rows returned={len(results)}")
    return results
