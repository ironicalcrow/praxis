import uuid
from datetime import datetime

from fastapi import HTTPException

from app.core.session import get_session
from app.modules.jobs.models import Job
from app.modules.application.models import (
    Application,
    ApplicationStatus,
    ApplicationStatusHistory,
    ApplicationNote,
)


def create_job_to_db(db, job_data: dict):
    """Create or reuse a job from job search result."""

    # Reuse if frontend sent the DB id directly (suggestion pool jobs already exist)
    explicit_id = job_data.get("id")
    if explicit_id:
        existing = db.query(Job).filter(Job.id == str(explicit_id)).first()
        if existing:
            return existing

    external_id = job_data.get("external_id")
    if external_id:
        existing = db.query(Job).filter(Job.external_id == external_id).first()
        if existing:
            return existing

    new_job = Job(
        id=str(uuid.uuid4()),
        external_id=external_id,
        title=job_data.get("title"),
        company_name=job_data.get("company_name") or job_data.get("company", ""),
        company_website=job_data.get("company_website"),
        publisher=job_data.get("publisher"),
        job_types=job_data.get("job_types"),
        location=job_data.get("location"),
        is_remote=job_data.get("is_remote", False),
        apply_urls=job_data.get("apply_urls"),
        description=job_data.get("description"),
        salary=job_data.get("salary"),
        experience_level=job_data.get("experience_level"),
        skills_and_technologies=job_data.get("skills_and_technologies"),
        responsibilities=job_data.get("responsibilities"),
        qualifications=job_data.get("qualifications"),
        benefits=job_data.get("benefits"),
        job_metadata=job_data,
    )

    db.add(new_job)
    db.flush()

    return new_job


def create_application_to_db(
    db,
    user_id: str,
    job_title: str,
    company: str,
    job_id: str | None = None,
    location: str | None = None,
    apply_url: str | None = None,
    source: str | None = None,
    salary: str | None = None,
    status: ApplicationStatus = ApplicationStatus.APPLIED,
):
    """Create an application."""

    user_uuid = str(user_id)

    if job_id:
        existing_application = (
            db.query(Application)
            .filter(
                Application.user_id == user_uuid,
                Application.job_id == job_id,
                Application.is_archived == False,
            )
            .first()
        )

        if existing_application:
            raise HTTPException(
                status_code=409,
                detail="Application already exists for this job",
            )

    application_id = str(uuid.uuid4())

    new_application = Application(
        id=application_id,
        user_id=user_uuid,
        job_id=job_id,
        job_title=job_title,
        company=company,
        location=location,
        apply_url=apply_url,
        source=source,
        salary=salary,
        status=status,
        applied_at=datetime.utcnow(),
        last_status_changed_at=datetime.utcnow(),
        is_archived=False,
    )

    db.add(new_application)
    db.flush()

    create_application_status_history_to_db(
        db=db,
        application_id=application_id,
        old_status=None,
        new_status=status,
        user_id=user_id,
    )

    return new_application


def create_application_status_history_to_db(
    db,
    application_id: str,
    old_status,
    new_status,
    user_id: str,
    reason: str | None = None,
):
    """Create application status history."""

    user_uuid = str(user_id)

    status_history = ApplicationStatusHistory(
        id=str(uuid.uuid4()),
        application_id=application_id,
        old_status=old_status,
        new_status=new_status,
        changed_by_user_id=user_uuid,
        reason=reason,
    )

    db.add(status_history)
    db.flush()

    return status_history


def create_application_from_job_db(user_id: str, job_data: dict):
    """Create job first, then create application from that job with status=applied.

    If an application already exists with status=saved (e.g. bookmarked by chatbot),
    promote it to applied instead of raising 409.
    """

    db = get_session()

    try:
        job = create_job_to_db(db=db, job_data=job_data)

        user_uuid = str(user_id)
        existing = (
            db.query(Application)
            .filter(
                Application.user_id == user_uuid,
                Application.job_id == job.id,
                Application.is_archived == False,
            )
            .first()
        )

        if existing:
            if existing.status == ApplicationStatus.SAVED:
                existing.status = ApplicationStatus.APPLIED
                existing.last_status_changed_at = datetime.utcnow()
                create_application_status_history_to_db(
                    db=db,
                    application_id=existing.id,
                    old_status=ApplicationStatus.SAVED,
                    new_status=ApplicationStatus.APPLIED,
                    user_id=user_id,
                )
                db.commit()
                return {"application_id": existing.id, "job_id": job.id, "message": "Application promoted to applied"}
            else:
                raise HTTPException(status_code=409, detail="Application already exists for this job")

        apply_url = (job.apply_urls[0] if job.apply_urls else None)
        application = create_application_to_db(
            db=db,
            user_id=user_id,
            job_id=job.id,
            job_title=job.title,
            company=job.company_name,
            location=job.location,
            apply_url=apply_url,
            salary=job.salary,
            status=ApplicationStatus.APPLIED,
        )

        db.commit()

        return {
            "application_id": application.id,
            "job_id": job.id,
            "message": "Application created from job successfully",
        }

    except HTTPException:
        db.rollback()
        raise

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create application from job: {str(e)}",
        )

    finally:
        db.close()


def create_manual_application_db(
    user_id: str,
    job_title: str,
    company: str,
    location: str | None = None,
    apply_url: str | None = None,
    source: str | None = "manual",
    salary: str | None = None,
):
    """Create manual application."""

    db = get_session()

    try:
        application = create_application_to_db(
            db=db,
            user_id=user_id,
            job_id=None,
            job_title=job_title,
            company=company,
            location=location,
            apply_url=apply_url,
            source=source,
            salary=salary,
        )

        db.commit()

        return {
            "application_id": application.id,
            "message": "Manual application created successfully",
        }

    except HTTPException:
        db.rollback()
        raise

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create manual application: {str(e)}",
        )

    finally:
        db.close()


def fetch_applications_from_db(
    user_id: str,
    status: str | None = None,
    include_archived: bool = False,
):
    """Fetch all applications for a user."""

    db = get_session()

    try:
        user_uuid = str(user_id)

        query = db.query(Application).filter(Application.user_id == user_uuid)

        if not include_archived:
            query = query.filter(Application.is_archived == False)

        if status:
            try:
                status_enum = ApplicationStatus(status)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid application status",
                )

            query = query.filter(Application.status == status_enum)

        applications = query.order_by(Application.created_at.desc()).all()

        return [
            serialize_application_from_db(db, application)
            for application in applications
        ]

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch applications: {str(e)}",
        )

    finally:
        db.close()


def fetch_kanban_applications_from_db(user_id: str):
    """Fetch applications grouped by Kanban status."""

    db = get_session()

    try:
        user_uuid = str(user_id)

        applications = (
            db.query(Application)
            .filter(
                Application.user_id == user_uuid,
                Application.is_archived == False,
            )
            .order_by(Application.created_at.desc())
            .all()
        )

        kanban = {
            "saved": [],
            "applied": [],
            "interviewing": [],
            "offer": [],
            "rejected": [],
        }

        for application in applications:
            kanban[application.status.value].append(
                serialize_application_from_db(db, application)
            )

        return kanban

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch kanban applications: {str(e)}",
        )

    finally:
        db.close()


def update_application_status_db(
    user_id: str,
    application_id: str,
    new_status: str,
    reason: str | None = None,
):
    """Update application status and store history."""

    db = get_session()

    try:
        user_uuid = str(user_id)

        application = (
            db.query(Application)
            .filter(
                Application.id == application_id,
                Application.user_id == user_uuid,
            )
            .first()
        )

        if not application:
            raise HTTPException(
                status_code=404,
                detail="Application not found",
            )

        try:
            new_status_enum = ApplicationStatus(new_status)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Invalid application status",
            )

        old_status = application.status

        application.status = new_status_enum
        application.last_status_changed_at = datetime.utcnow()

        create_application_status_history_to_db(
            db=db,
            application_id=application.id,
            old_status=old_status,
            new_status=new_status_enum,
            user_id=user_id,
            reason=reason,
        )

        db.commit()

        return {
            "application_id": application.id,
            "old_status": old_status.value if old_status else None,
            "new_status": new_status_enum.value,
            "message": "Application status updated successfully",
        }

    except HTTPException:
        db.rollback()
        raise

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update application status: {str(e)}",
        )

    finally:
        db.close()


def add_application_note_db(
    user_id: str,
    application_id: str,
    content: str,
):
    """Add note to application."""

    db = get_session()

    try:
        user_uuid = str(user_id)

        application = (
            db.query(Application)
            .filter(
                Application.id == application_id,
                Application.user_id == user_uuid,
            )
            .first()
        )

        if not application:
            raise HTTPException(
                status_code=404,
                detail="Application not found",
            )

        note_id = str(uuid.uuid4())

        note = ApplicationNote(
            id=note_id,
            application_id=application_id,
            user_id=user_uuid,
            content=content,
        )

        db.add(note)
        db.commit()

        return {
            "note_id": note_id,
            "application_id": application_id,
            "message": "Note added successfully",
        }

    except HTTPException:
        db.rollback()
        raise

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to add application note: {str(e)}",
        )

    finally:
        db.close()


def update_application_note_db(
    user_id: str,
    note_id: str,
    content: str,
):
    """Update application note."""

    db = get_session()

    try:
        user_uuid = str(user_id)

        note = (
            db.query(ApplicationNote)
            .filter(
                ApplicationNote.id == note_id,
                ApplicationNote.user_id == user_uuid,
            )
            .first()
        )

        if not note:
            raise HTTPException(
                status_code=404,
                detail="Note not found",
            )

        note.content = content

        db.commit()

        return {
            "note_id": note.id,
            "application_id": note.application_id,
            "message": "Note updated successfully",
        }

    except HTTPException:
        db.rollback()
        raise

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update application note: {str(e)}",
        )

    finally:
        db.close()


def archive_application_db(user_id: str, application_id: str):
    """Archive application."""

    db = get_session()

    try:
        user_uuid = str(user_id)

        application = (
            db.query(Application)
            .filter(
                Application.id == application_id,
                Application.user_id == user_uuid,
            )
            .first()
        )

        if not application:
            raise HTTPException(
                status_code=404,
                detail="Application not found",
            )

        application.is_archived = True

        db.commit()

        return {
            "application_id": application.id,
            "message": "Application archived successfully",
        }

    except HTTPException:
        db.rollback()
        raise

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to archive application: {str(e)}",
        )

    finally:
        db.close()


def delete_application_db(user_id: str, application_id: str):
    """Delete application permanently."""

    db = get_session()

    try:
        user_uuid = str(user_id)

        application = (
            db.query(Application)
            .filter(
                Application.id == application_id,
                Application.user_id == user_uuid,
            )
            .first()
        )

        if not application:
            raise HTTPException(
                status_code=404,
                detail="Application not found",
            )

        db.delete(application)
        db.commit()

        return {
            "deleted": True,
            "application_id": application_id,
            "message": "Application deleted successfully",
        }

    except HTTPException:
        db.rollback()
        raise

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete application: {str(e)}",
        )

    finally:
        db.close()


def serialize_application_from_db(db, application: Application):
    """Serialize application with notes and status history."""

    notes = (
        db.query(ApplicationNote)
        .filter(ApplicationNote.application_id == application.id)
        .order_by(ApplicationNote.created_at.desc())
        .all()
    )

    status_history = (
        db.query(ApplicationStatusHistory)
        .filter(ApplicationStatusHistory.application_id == application.id)
        .order_by(ApplicationStatusHistory.changed_at.desc())
        .all()
    )

    return {
        "id": application.id,
        "user_id": str(application.user_id),
        "job_id": application.job_id,
        "job_title": application.job_title,
        "company": application.company,
        "location": application.location,
        "apply_url": application.apply_url,
        "source": application.source,
        "salary": application.salary,
        "status": application.status.value,
        "applied_at": application.applied_at.isoformat() if application.applied_at else None,
        "last_status_changed_at": application.last_status_changed_at.isoformat()
        if application.last_status_changed_at
        else None,
        "is_archived": application.is_archived,
        "notes": [
            {
                "id": note.id,
                "application_id": note.application_id,
                "content": note.content,
                "created_at": note.created_at.isoformat() if note.created_at else None,
                "updated_at": note.updated_at.isoformat() if note.updated_at else None,
            }
            for note in notes
        ],
        "status_history": [
            {
                "id": history.id,
                "old_status": history.old_status.value if history.old_status else None,
                "new_status": history.new_status.value,
                "reason": history.reason,
                "changed_at": history.changed_at.isoformat() if history.changed_at else None,
                "changed_by_user_id": str(history.changed_by_user_id)
                if history.changed_by_user_id
                else None,
            }
            for history in status_history
        ],
        "created_at": application.created_at.isoformat() if application.created_at else None,
        "updated_at": application.updated_at.isoformat() if application.updated_at else None,
    }