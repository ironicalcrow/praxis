from fastapi import APIRouter, HTTPException, Query

from app.modules.jobs.providers.jsearch import JSearchError
from app.schemas import (
    JobDetailResponse,
    JobSearchRequest,
    JobSearchResponse,
)
from app.modules.jobs.service import get_job_detail, search_live_jobs

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
async def read_job_detail(
    job_id: str,
    country: str = Query(default="us"),
):
    try:
        return await get_job_detail(
            job_id=job_id,
            country=country,
        )

    except JSearchError as e:
        raise HTTPException(status_code=400, detail=str(e))