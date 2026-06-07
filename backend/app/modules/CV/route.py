import asyncio
import tempfile
import uuid
from pathlib import Path
from uuid import UUID as PUUID

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends

from app.modules.CV.cv import resume_parser
from app.modules.CV.db_service import (
    save_resume_to_db,
    fetch_resume_from_db,
    update_resume_embedding,
    save_cv_upload_record,
    get_cv_upload_history,
    get_cv_upload_by_id,
    set_active_cv_upload,
)
from app.modules.CV.schemas import ResumeSchema, ResumeResponse, UploadCVResponse, CVUploadRecord
from app.modules.auth.dependency import get_current_user
from app.core.llm_caller import embed_text


router = APIRouter()


def _write_temp(file_bytes: bytes, suffix: str) -> str:
    """Write bytes to a NamedTemporaryFile. Returns the temp file path."""
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    try:
        tmp.write(file_bytes)
    finally:
        tmp.close()
    return tmp.name


async def _run_background_steps(resume_id: str, resume_obj: ResumeSchema, user_id: str, parsed_resume):
    """Embed → generate queries → invalidate pool. All best-effort."""
    try:
        loc = parsed_resume.get("location") if isinstance(parsed_resume, dict) else parsed_resume.location
        skills = parsed_resume.get("skills", []) if isinstance(parsed_resume, dict) else parsed_resume.skills
        raw = parsed_resume.get("raw_text", "") if isinstance(parsed_resume, dict) else parsed_resume.raw_text
        exp_list = parsed_resume.get("experience", []) if isinstance(parsed_resume, dict) else parsed_resume.experience

        resume_text = ""
        if loc:
            resume_text += f"Location: {loc}. "
        resume_text += "Skills: " + ", ".join(skills or []) + ". "
        if raw:
            resume_text += raw[:500] + "... "
        for exp in (exp_list or []):
            role = exp.get("role") if isinstance(exp, dict) else exp.role
            org = exp.get("organization") if isinstance(exp, dict) else exp.organization
            desc = exp.get("description") if isinstance(exp, dict) else exp.description
            resume_text += f"{role} at {org}: {desc}. "

        vector = await embed_text(resume_text)
        await asyncio.to_thread(update_resume_embedding, resume_id, vector)
        print("[CV] ✅ Resume embedding saved.")
    except Exception as e:
        print(f"[CV] ⚠️ Embedding failed: {e}.")

    try:
        from app.modules.jobs.services.query_service import refresh_resume_job_queries
        await refresh_resume_job_queries(resume_id, resume_obj)
        print("[CV] ✅ Job queries generated.")
    except Exception as e:
        print(f"[CV] ⚠️ Query generation failed: {e}.")

    try:
        from app.modules.jobs.services.job_suggestion import async_invalidate_pool
        await async_invalidate_pool(user_id)
    except Exception as e:
        print(f"[CV] ⚠️ Pool invalidation failed: {e}.")


@router.post("/upload-cv", response_model=UploadCVResponse)
async def upload_cv(
    file: UploadFile = File(...),
    current_user=Depends(get_current_user),
):
    allowed_extensions = [".pdf", ".docx", ".png", ".jpg", ".jpeg"]
    extension = Path(file.filename).suffix.lower()
    if extension not in allowed_extensions:
        raise HTTPException(status_code=400, detail="Unsupported file format")

    file_bytes = await file.read()
    unique_filename = f"{uuid.uuid4()}{extension}"
    user_id = str(current_user.id)

    # Write to OS temp dir — auto-cleaned after use
    temp_path = await asyncio.to_thread(_write_temp, file_bytes, extension)

    try:
        # Step 1: Parse CV + save to DB (must succeed)
        parsed_resume = await resume_parser(temp_path)
        db_result = save_resume_to_db(parsed_resume=parsed_resume, user_id=current_user.id)
        resume_id = str(db_result["resume_id"])
        resume_obj = ResumeSchema(**parsed_resume) if isinstance(parsed_resume, dict) else parsed_resume

        # Step 2: Upload to Supabase Storage (best-effort)
        file_url = None
        try:
            from app.core.supabase_storage import upload_cv as supabase_upload
            storage_path = f"{user_id}/{unique_filename}"
            file_url = await asyncio.to_thread(supabase_upload, file_bytes, storage_path)
            await asyncio.to_thread(save_cv_upload_record, user_id, file_url, storage_path, file.filename)
            save_resume_to_db(parsed_resume=parsed_resume, user_id=current_user.id, file_url=file_url)
            print(f"[CV] ✅ Uploaded to Supabase: {file_url}")
        except Exception as e:
            print(f"[CV] ⚠️ Supabase upload failed: {e}. CV saved without file_url.")

        # Steps 3–5: embed, queries, pool — best-effort
        await _run_background_steps(resume_id, resume_obj, user_id, parsed_resume)

        return {
            "success": True,
            "message": "CV uploaded, parsed, and saved successfully",
            "resume_id": db_result["resume_id"],
            "file_url": file_url,
            "data": parsed_resume,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Always delete the temp file — no local files retained
        try:
            import os
            os.unlink(temp_path)
        except Exception:
            pass


@router.get("/my-cv", response_model=ResumeResponse)
async def get_my_cv(current_user=Depends(get_current_user)):
    return fetch_resume_from_db(current_user.id)


@router.get("/uploads", response_model=list[CVUploadRecord])
async def list_cv_uploads(current_user=Depends(get_current_user)):
    """Return all past CV uploads for the authenticated user, newest first."""
    return await asyncio.to_thread(get_cv_upload_history, str(current_user.id))


@router.post("/uploads/{upload_id}/activate", response_model=UploadCVResponse)
async def activate_past_cv(upload_id: PUUID, current_user=Depends(get_current_user)):
    upload_id = str(upload_id)
    """
    Download a past CV from Supabase, re-parse it, make it the active CV,
    then run the full downstream flow (embed → queries → invalidate pool).
    """
    record = await asyncio.to_thread(get_cv_upload_by_id, upload_id, str(current_user.id))
    if not record:
        raise HTTPException(status_code=404, detail="Upload not found")

    try:
        from app.core.supabase_storage import download_cv
        file_bytes = await asyncio.to_thread(download_cv, record["storage_path"])
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to download CV from storage: {e}")

    ext = Path(record["original_filename"] or "resume.pdf").suffix or ".pdf"
    temp_path = await asyncio.to_thread(_write_temp, file_bytes, ext)

    try:
        user_id = str(current_user.id)

        parsed_resume = await resume_parser(temp_path)
        db_result = save_resume_to_db(
            parsed_resume=parsed_resume,
            user_id=current_user.id,
            file_url=record["file_url"],
        )
        resume_id = str(db_result["resume_id"])
        resume_obj = ResumeSchema(**parsed_resume) if isinstance(parsed_resume, dict) else parsed_resume

        await asyncio.to_thread(set_active_cv_upload, upload_id, user_id)
        print(f"[CVActivate] ✅ Upload {upload_id} marked as active.")

        await _run_background_steps(resume_id, resume_obj, user_id, parsed_resume)

        return {
            "success": True,
            "message": "CV activated successfully",
            "resume_id": db_result["resume_id"],
            "file_url": record["file_url"],
            "data": parsed_resume,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        try:
            import os
            os.unlink(temp_path)
        except Exception:
            pass
