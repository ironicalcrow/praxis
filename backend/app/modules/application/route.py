from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, Dict, Any

from app.modules.application.db_service import (
    create_application_from_job_db,
    create_manual_application_db,
    fetch_applications_from_db,
    fetch_kanban_applications_from_db,
    update_application_status_db,
    add_application_note_db,
    update_application_note_db,
    archive_application_db,
    delete_application_db,
)

from app.modules.application.schemas import (
    ApplicationCreation,
    ApplicationCreationManual,
    UpdateStatusRequest,
    ApplicationNoteRequest,
    ApplicationNoteRespone,
    ApplicationStatusHistoryResponse,
    ApplicationResponse,
    DeleteApplicationResponse,
)


router = APIRouter(
    prefix="/application",
    tags=["application"],
)





@router.post("/applications/from-job")
def create_application_from_job(payload: ApplicationCreation):
    try:
        return create_application_from_job_db(
            user_id=payload.user_id,
            job_data=payload.job,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create application from job: {str(e)}",
        )


@router.post("/applications/manual")
def create_manual_application(payload: ApplicationCreationManual):
    try:
        return create_manual_application_db(
            user_id=payload.user_id,
            job_title=payload.job_title,
            company=payload.company,
            location=payload.location,
            apply_url=payload.apply_url,
            source=payload.source,
            salary=payload.salary,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create manual application: {str(e)}",
        )


@router.get("/applications")
def get_applications(
    user_id: str = Query(...),
    status: Optional[str] = Query(None),
    include_archived: bool = Query(False),
):
    try:
        return fetch_applications_from_db(
            user_id=user_id,
            status=status,
            include_archived=include_archived,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch applications: {str(e)}",
        )


@router.get("/applications/kanban")
def get_kanban_applications(user_id: str = Query(...)):
    try:
        return fetch_kanban_applications_from_db(user_id=user_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch kanban applications: {str(e)}",
        )


@router.patch("/applications/{application_id}/status")
def update_application_status(
    application_id: str,
    payload: UpdateStatusRequest,
):

    try:
        return update_application_status_db(
            user_id=payload.user_id,
            application_id=application_id,
            new_status=payload.status,
            reason=payload.reason,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update application status: {str(e)}",
        )


@router.post("/applications/{application_id}/notes")
def add_application_note(
    application_id: str,
    payload: ApplicationNoteRequest,
):
    try:
        return add_application_note_db(
            user_id=payload.user_id,
            application_id=application_id,
            content=payload.content,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to add application note: {str(e)}",
        )


@router.patch("/notes/{note_id}")
def update_application_note(
    note_id: str,
    payload: ApplicationNoteRequest,
):
    try:
        return update_application_note_db(
            user_id=payload.user_id,
            note_id=note_id,
            content=payload.content,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update application note: {str(e)}",
        )


@router.patch("/applications/{application_id}/archive")
def archive_application(
    application_id: str,
    user_id: str = Query(...),
):

    try:
        return archive_application_db(
            user_id=user_id,
            application_id=application_id,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to archive application: {str(e)}",
        )


@router.delete("/applications/{application_id}")
def delete_application(
    application_id: str,
    user_id: str = Query(...),
):
    try:
        return delete_application_db(
            user_id=user_id,
            application_id=application_id,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete application: {str(e)}",
        )