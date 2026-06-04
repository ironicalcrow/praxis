from fastapi import APIRouter, Depends, HTTPException

from app.modules.auth.dependency import get_current_user
from app.modules.CV.db_service import fetch_resume_from_db
from app.modules.CV.schemas import ResumeSchema
from app.modules.fit_score.service import calculate_job_fit_score
from app.modules.jobs.controller import get_job_detail, search_live_jobs
from app.modules.jobs.providers.jsearch import JSearchError
from app.modules.jobs.services.job_profile_extreactor import JobProfileExtractorError
from app.modules.jobs.services.job_suggestion import build_job_pool_from_queries
from app.schemas import (
    JobDetailResponse,
    JobDetailWithFitResponse,
    JobSearchRequest,
    JobSearchResponse,
)
from app.modules.jobs.schema import JobSuggestionRequest

router = APIRouter(prefix="/jobs", tags=["Jobs"])


@router.post("/live-search", response_model=JobSearchResponse)
async def live_search_jobs(request: JobSearchRequest):
    try:
        jobs = await search_live_jobs(
            query=request.query,
            location=request.location,
            page=request.page,
            num_pages=request.num_pages,
            country=request.country,
            date_posted=request.date_posted,
        )

        return JobSearchResponse(
            query=request.query,
            total=len(jobs),
            jobs=jobs,
        )

    except JSearchError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/details/{job_id}", response_model=JobDetailResponse)
async def read_job_detail(job_id: str):
    try:
        return await get_job_detail(job_id=job_id)

    except JSearchError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/details/{job_id}/fit-score", response_model=JobDetailWithFitResponse)
async def read_job_detail_with_fit_score(
    job_id: str,
    current_user=Depends(get_current_user),
):
    try:
        return await calculate_job_fit_score(
            job_id=job_id,
            current_user=current_user,
        )

    except JSearchError as e:
        raise HTTPException(status_code=400, detail=str(e))

    except JobProfileExtractorError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/suggest-from-my-cv")
async def suggest_jobs_from_my_cv(
    request: JobSuggestionRequest,
    current_user=Depends(get_current_user),
):
    try:
        resume_data = fetch_resume_from_db(current_user.id)
        candidate_resume = ResumeSchema(**resume_data)

        ranked_jobs = await build_job_pool_from_queries(
            queries=request.queries,
            candidate_resume=candidate_resume,
            location=request.location,
            country=request.country,
            page=request.page,
            num_pages=request.num_pages,
            max_jobs_per_query=request.max_jobs_per_query,
            max_total_jobs=request.max_total_jobs,
        )

        return {
            "total": len(ranked_jobs),
            "jobs": ranked_jobs,
        }

    except JSearchError as e:
        raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
