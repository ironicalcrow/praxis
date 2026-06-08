from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from app.modules.auth.dependency import get_current_user
from app.modules.CV.db_service import fetch_resume_from_db
from app.modules.CV.schemas import ResumeSchema
from app.modules.jobs.controller import (
    calculate_job_fit_score,
    get_job_detail,
    search_live_jobs,
    get_user_preferences,
    update_user_preferences,
)
from app.modules.jobs.services.job_suggestion import (
    build_suggestion_pool,
    get_suggestion_window,
    advance_suggestion_window,
)
from app.modules.jobs.services.query_service import (
    get_or_generate_resume_job_queries,
    delete_job_queries,
    refresh_resume_job_queries,
)
from app.schemas import (
    JobSchema,
    JobSearchRequest,
    JobSearchResponse,
    UserPreferenceCreate,
    UserPreferenceUpdate,
    UserPreferenceResponse,
    SuggestionWindowResponse,
)


router = APIRouter(prefix="/jobs", tags=["Jobs"])


@router.post("/live-search", response_model=JobSearchResponse)
async def live_search_jobs(
    request: JobSearchRequest,
    current_user=Depends(get_current_user),
):
    try:
        resume_data = fetch_resume_from_db(current_user.id)
        resume_id = str(resume_data["id"])

        jobs = await search_live_jobs(
            query=request.query,
            user_id=current_user.id,
            resume_id=resume_id,
            location=request.location,
            page=request.page,
            num_pages=request.num_pages,
            country=request.country,
            remote_jobs_only=request.remote_jobs_only,
        )

        return JobSearchResponse(query=request.query, total=len(jobs), jobs=jobs)

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/details/{job_id}", response_model=JobSchema)
async def read_job_detail(job_id: UUID, current_user=Depends(get_current_user)):
    job_id = str(job_id)
    try:
        return await get_job_detail(job_id=job_id, current_user=current_user)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/suggest-from-my-cv", response_model=SuggestionWindowResponse)
async def suggest_jobs_from_my_cv(current_user=Depends(get_current_user)):
    """
    Return the current suggestion window (10 jobs). Idempotent — does not advance the cursor.
    Builds the pool on first call (or if pool expired). Falls back gracefully if DB is empty.
    """
    try:
        resume_data = fetch_resume_from_db(current_user.id)
        if not resume_data:
            raise HTTPException(status_code=404, detail="No CV found. Please upload your CV first.")

        candidate_resume = ResumeSchema(**resume_data)
        resume_id = str(resume_data["id"])
        user_id = str(current_user.id)

        queries = await get_or_generate_resume_job_queries(resume_id, candidate_resume)

        window = await get_suggestion_window(user_id)
        if window is None:
            window = await build_suggestion_pool(user_id, candidate_resume, queries)

        return window

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/suggest-from-my-cv/refresh", response_model=SuggestionWindowResponse)
async def refresh_suggestion_window(current_user=Depends(get_current_user)):
    """
    Advance the suggestion cursor by one window and return the next 10 jobs.
    Triggers background prefetch at 60% consumed, cycles + regenerates at 100%.
    """
    try:
        resume_data = fetch_resume_from_db(current_user.id)
        if not resume_data:
            raise HTTPException(status_code=404, detail="No CV found. Please upload your CV first.")

        candidate_resume = ResumeSchema(**resume_data)
        resume_id = str(resume_data["id"])
        user_id = str(current_user.id)

        queries = await get_or_generate_resume_job_queries(resume_id, candidate_resume)

        return await advance_suggestion_window(
            user_id=user_id,
            queries=queries,
            candidate_resume=candidate_resume,
            resume_id=resume_id,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/queries")
async def get_queries(current_user=Depends(get_current_user)):
    try:
        resume_data = fetch_resume_from_db(current_user.id)
        resume_id = str(resume_data["id"])
        from app.core.session import SessionLocal
        from app.modules.jobs.models import JobQuery
        with SessionLocal() as db:
            queries = (
                db.query(JobQuery)
                .filter(JobQuery.resume_id == str(resume_id))
                .order_by(JobQuery.priority.desc(), JobQuery.added_at.desc())
                .all()
            )
            return {"queries": [q.query for q in queries]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/queries/refresh")
async def refresh_queries(current_user=Depends(get_current_user)):
    """Dev / power-user endpoint: wipe and regenerate LLM queries, clear suggestion pool."""
    try:
        resume_data = fetch_resume_from_db(current_user.id)
        candidate_resume = ResumeSchema(**resume_data)
        resume_id = str(resume_data["id"])
        user_id = str(current_user.id)

        new_queries = await refresh_resume_job_queries(resume_id, candidate_resume)

        # Clear suggestion pool so next GET rebuilds
        from app.modules.jobs.services.job_suggestion import async_invalidate_pool
        await async_invalidate_pool(user_id)

        return {"queries": new_queries, "message": "Queries refreshed. Suggestion pool will rebuild on next load."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/preferences", response_model=UserPreferenceResponse)
async def get_preferences(current_user=Depends(get_current_user)):
    try:
        return await get_user_preferences(str(current_user.id))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/preferences", response_model=UserPreferenceResponse)
async def update_preferences(prefs: UserPreferenceUpdate, current_user=Depends(get_current_user)):
    """
    Update job type preferences (Remote, Hybrid, Full-time, etc.).
    Regenerates preference embedding and invalidates suggestion pool automatically.
    """
    try:
        updated = await update_user_preferences(
            str(current_user.id),
            prefs.model_dump(exclude_unset=True),
        )

        # Trigger background query refresh so new preferences influence future scraping
        try:
            resume_data = fetch_resume_from_db(current_user.id)
            if resume_data:
                candidate_resume = ResumeSchema(**resume_data)
                resume_id = str(resume_data["id"])
                import asyncio
                asyncio.create_task(refresh_resume_job_queries(resume_id, candidate_resume))
        except Exception as e:
            print(f"[Preferences] Background query refresh failed to start: {e}")

        return updated
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
